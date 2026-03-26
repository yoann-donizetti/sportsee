"""Gestion du vector store FAISS pour le pipeline RAG.

Ce module permet de :
- charger des documents déjà parsés ;
- les découper en chunks ;
- générer des embeddings avec Mistral ;
- construire un index FAISS ;
- sauvegarder / recharger l'index et les chunks ;
- effectuer une recherche sémantique.

Points importants :
- les chemins sont gérés avec pathlib pour fiabiliser la sauvegarde ;
- l'index utilise une similarité cosinus (via normalisation L2 + IndexFlatIP) ;
- les logs permettent de suivre les étapes principales de l'indexation.
"""

import logging
import pickle
from pathlib import Path
from typing import Any, Dict, List, Optional

import faiss
import numpy as np
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from mistralai.client import MistralClient
from mistralai.exceptions import MistralAPIException

from .config import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    DOCUMENT_CHUNKS_FILE,
    EMBEDDING_BATCH_SIZE,
    EMBEDDING_MODEL,
    FAISS_INDEX_FILE,
    MISTRAL_API_KEY,
    SEARCH_K,
)

logger = logging.getLogger(__name__)


class VectorStoreManager:
    """Gère la création, le chargement et la recherche dans un index FAISS."""

    def __init__(self) -> None:
        """
        Initialise le gestionnaire du vector store.

        Attributs :
        - self.index : index FAISS chargé ou créé ;
        - self.document_chunks : liste des chunks indexés ;
        - self.index_file : chemin absolu du fichier d'index FAISS ;
        - self.chunks_file : chemin absolu du fichier de chunks sérialisés ;
        - self.mistral_client : client API Mistral.
        """
        self.index: Optional[faiss.Index] = None
        self.document_chunks: List[Dict[str, Any]] = []

        # Conversion en chemins absolus robustes
        self.index_file = Path(FAISS_INDEX_FILE).resolve()
        self.chunks_file = Path(DOCUMENT_CHUNKS_FILE).resolve()

        self.mistral_client = MistralClient(api_key=MISTRAL_API_KEY)
        self._load_index_and_chunks()

    def _load_index_and_chunks(self) -> None:
        """Charge l'index FAISS et les chunks si les fichiers existent déjà."""
        if self.index_file.exists() and self.chunks_file.exists():
            try:
                logger.info("Chargement de l'index Faiss depuis %s...", self.index_file)
                self.index = faiss.read_index(str(self.index_file))

                logger.info("Chargement des chunks depuis %s...", self.chunks_file)
                with open(self.chunks_file, "rb") as f:
                    self.document_chunks = pickle.load(f)

                logger.info(
                    "Index (%s vecteurs) et %s chunks chargés.",
                    self.index.ntotal,
                    len(self.document_chunks),
                )

            except Exception as e:
                logger.error("Erreur lors du chargement de l'index/chunks: %s", e)
                self.index = None
                self.document_chunks = []
        else:
            logger.warning(
                "Fichiers d'index Faiss ou de chunks non trouvés. L'index est vide."
            )

    def _split_documents_to_chunks(
        self, documents: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Découpe les documents en chunks avec leurs métadonnées."""
        logger.info(
            "Découpage de %s documents en chunks (taille=%s, chevauchement=%s)...",
            len(documents),
            CHUNK_SIZE,
            CHUNK_OVERLAP,
        )

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            length_function=len,
            add_start_index=True,
        )

        all_chunks: List[Dict[str, Any]] = []
        doc_counter = 0

        for doc in documents:
            # Conversion de notre structure vers le format LangChain
            langchain_doc = Document(
                page_content=doc["page_content"],
                metadata=doc["metadata"],
            )

            chunks = text_splitter.split_documents([langchain_doc])

            logger.info(
                "Document '%s' découpé en %s chunks.",
                doc["metadata"].get("filename", "N/A"),
                len(chunks),
            )

            for i, chunk in enumerate(chunks):
                chunk_dict = {
                    "id": f"{doc_counter}_{i}",
                    "text": chunk.page_content,
                    "metadata": {
                        **chunk.metadata,
                        "chunk_id_in_doc": i,
                        "start_index": chunk.metadata.get("start_index", -1),
                    },
                }
                all_chunks.append(chunk_dict)

            doc_counter += 1

        logger.info("Total de %s chunks créés.", len(all_chunks))
        return all_chunks

    def _generate_embeddings(
        self, chunks: List[Dict[str, Any]]
    ) -> Optional[np.ndarray]:
        """Génère les embeddings pour une liste de chunks via l'API Mistral."""
        if not MISTRAL_API_KEY:
            logger.error(
                "Impossible de générer les embeddings: MISTRAL_API_KEY manquante."
            )
            return None

        if not chunks:
            logger.warning("Aucun chunk fourni pour générer les embeddings.")
            return None

        logger.info(
            "Génération des embeddings pour %s chunks (modèle: %s)...",
            len(chunks),
            EMBEDDING_MODEL,
        )

        all_embeddings: List[List[float]] = []
        total_batches = (len(chunks) + EMBEDDING_BATCH_SIZE - 1) // EMBEDDING_BATCH_SIZE

        for i in range(0, len(chunks), EMBEDDING_BATCH_SIZE):
            batch_num = (i // EMBEDDING_BATCH_SIZE) + 1
            batch_chunks = chunks[i : i + EMBEDDING_BATCH_SIZE]
            texts_to_embed = [chunk["text"] for chunk in batch_chunks]

            logger.info(
                "Traitement du lot %s/%s (%s chunks)",
                batch_num,
                total_batches,
                len(texts_to_embed),
            )

            try:
                response = self.mistral_client.embeddings(
                    model=EMBEDDING_MODEL,
                    input=texts_to_embed,
                )
                batch_embeddings = [data.embedding for data in response.data]
                all_embeddings.extend(batch_embeddings)

            except MistralAPIException as e:
                logger.error(
                    "Erreur API Mistral lors de la génération d'embeddings (lot %s): %s",
                    batch_num,
                    e,
                )
                logger.error(
                    "Détails: Status Code=%s, Message=%s",
                    e.status_code,
                    e.message,
                )

            except Exception as e:
                logger.error(
                    "Erreur inattendue lors de la génération d'embeddings (lot %s): %s",
                    batch_num,
                    e,
                )

                # Si un lot échoue, on ajoute des vecteurs nuls pour ne pas casser
                # complètement le pipeline, à condition de connaître la dimension.
                num_failed = len(texts_to_embed)
                if all_embeddings:
                    dim = len(all_embeddings[0])
                else:
                    logger.error(
                        "Impossible de déterminer la dimension des embeddings, saut du lot."
                    )
                    continue

                logger.warning(
                    "Ajout de %s vecteurs nuls de dimension %s pour le lot échoué.",
                    num_failed,
                    dim,
                )
                all_embeddings.extend([np.zeros(dim, dtype="float32")] * num_failed)

        if not all_embeddings:
            logger.error("Aucun embedding n'a pu être généré.")
            return None

        embeddings_array = np.array(all_embeddings).astype("float32")
        logger.info(
            "Embeddings générés avec succès. Shape: %s",
            embeddings_array.shape,
        )
        return embeddings_array

    def build_index(self, documents: List[Dict[str, Any]]) -> None:
        """Construit l'index FAISS à partir des documents fournis."""
        if not documents:
            logger.warning("Aucun document fourni pour construire l'index.")
            return

        # 1. Découpage en chunks
        self.document_chunks = self._split_documents_to_chunks(documents)
        if not self.document_chunks:
            logger.error(
                "Le découpage n'a produit aucun chunk. Impossible de construire l'index."
            )
            return

        # 2. Génération des embeddings
        embeddings = self._generate_embeddings(self.document_chunks)
        if embeddings is None or embeddings.shape[0] != len(self.document_chunks):
            logger.error(
                "Problème de génération d'embeddings. Le nombre d'embeddings ne "
                "correspond pas au nombre de chunks."
            )

            self.document_chunks = []
            self.index = None

            # Nettoyage éventuel de fichiers existants
            if self.index_file.exists():
                self.index_file.unlink()
            if self.chunks_file.exists():
                self.chunks_file.unlink()

            return

        # 3. Création de l'index FAISS
        dimension = embeddings.shape[1]
        logger.info(
            "Création de l'index Faiss optimisé pour la similarité cosinus avec "
            "dimension %s...",
            dimension,
        )

        # Normalisation L2 pour simuler la similarité cosinus avec IndexFlatIP
        faiss.normalize_L2(embeddings)

        self.index = faiss.IndexFlatIP(dimension)
        self.index.add(embeddings)

        logger.info("Index Faiss créé avec %s vecteurs.", self.index.ntotal)

        # 4. Sauvegarde
        self._save_index_and_chunks()

    def _save_index_and_chunks(self) -> None:
        """Sauvegarde l'index FAISS et les chunks sérialisés."""
        if self.index is None or not self.document_chunks:
            logger.warning("Tentative de sauvegarde d'un index ou de chunks vides.")
            return

        # Création sûre des dossiers parents
        self.index_file.parent.mkdir(parents=True, exist_ok=True)
        self.chunks_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            logger.info("Sauvegarde de l'index Faiss dans %s...", self.index_file)
            faiss.write_index(self.index, str(self.index_file))

            logger.info("Sauvegarde des chunks dans %s...", self.chunks_file)
            with open(self.chunks_file, "wb") as f:
                pickle.dump(self.document_chunks, f)

            logger.info("Index et chunks sauvegardés avec succès.")

        except Exception as e:
            logger.error("Erreur lors de la sauvegarde de l'index/chunks: %s", e)

    def search(
        self,
        query_text: str,
        k: int = SEARCH_K,
        min_score: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """
        Recherche les k chunks les plus pertinents pour une requête.

        Args:
            query_text: Texte de la requête.
            k: Nombre de résultats à retourner.
            min_score: Score minimum (entre 0 et 1) pour inclure un résultat.

        Returns:
            Liste des chunks pertinents avec leurs scores.
        """
        if self.index is None or not self.document_chunks:
            logger.warning(
                "Recherche impossible: l'index Faiss n'est pas chargé ou est vide."
            )
            return []

        if not MISTRAL_API_KEY:
            logger.error(
                "Recherche impossible: MISTRAL_API_KEY manquante pour générer "
                "l'embedding de la requête."
            )
            return []

        logger.info("Recherche des %s chunks les plus pertinents pour: '%s'", k, query_text)

        try:
            # 1. Embedding de la requête
            response = self.mistral_client.embeddings(
                model=EMBEDDING_MODEL,
                input=[query_text],
            )
            query_embedding = np.array([response.data[0].embedding]).astype("float32")

            # Normalisation pour cohérence avec l'index
            faiss.normalize_L2(query_embedding)

            # 2. Recherche
            search_k = k * 3 if min_score is not None else k
            scores, indices = self.index.search(query_embedding, search_k)

            results: List[Dict[str, Any]] = []

            if indices.size > 0:
                for i, idx in enumerate(indices[0]):
                    if 0 <= idx < len(self.document_chunks):
                        chunk = self.document_chunks[idx]

                        raw_score = float(scores[0][i])
                        similarity = raw_score * 100

                        min_score_percent = min_score * 100 if min_score is not None else 0
                        if min_score is not None and similarity < min_score_percent:
                            logger.debug(
                                "Document filtré (score %.2f%% < minimum %.2f%%)",
                                similarity,
                                min_score_percent,
                            )
                            continue

                        results.append(
                            {
                                "score": similarity,
                                "raw_score": raw_score,
                                "text": chunk["text"],
                                "metadata": chunk["metadata"],
                            }
                        )
                    else:
                        logger.warning(
                            "Index Faiss %s hors limites (taille des chunks: %s).",
                            idx,
                            len(self.document_chunks),
                        )

            # 3. Tri et limitation
            results.sort(key=lambda x: x["score"], reverse=True)

            if len(results) > k:
                results = results[:k]

            if min_score is not None:
                min_score_percent = min_score * 100
                logger.info(
                    "%s chunks pertinents trouvés (score minimum: %.2f%%).",
                    len(results),
                    min_score_percent,
                )
            else:
                logger.info("%s chunks pertinents trouvés.", len(results))

            return results

        except MistralAPIException as e:
            logger.error(
                "Erreur API Mistral lors de la génération de l'embedding de la requête: %s",
                e,
            )
            logger.error(
                "Détails: Status Code=%s, Message=%s",
                e.status_code,
                e.message,
            )
            return []

        except Exception as e:
            logger.error("Erreur inattendue lors de la recherche: %s", e)
            return []