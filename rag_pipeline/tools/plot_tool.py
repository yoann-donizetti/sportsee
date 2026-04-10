import base64
import io
import json
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

import matplotlib.pyplot as plt
from langchain.tools import BaseTool
from pydantic import BaseModel, Field, ValidationError


class PlotPoint(BaseModel):
    label: str = Field(..., description="Libellé affiché sur l'axe X")
    value: float = Field(..., description="Valeur numérique associée")


class PlotToolInput(BaseModel):
    chart_type: Literal["bar", "line"] = Field(..., description="Type de graphique")
    title: str = Field(..., description="Titre du graphique")
    x_label: str = Field(default="", description="Label de l'axe X")
    y_label: str = Field(default="", description="Label de l'axe Y")
    data: List[PlotPoint] = Field(..., description="Points à tracer")
    return_base64: bool = Field(
        default=False,
        description="Si true, retourne une image encodée en base64 au lieu d'un chemin de fichier",
    )


def build_plot(payload: PlotToolInput) -> Dict[str, Any]:
    labels = [point.label for point in payload.data]
    values = [point.value for point in payload.data]

    fig, ax = plt.subplots(figsize=(10, 6))

    if payload.chart_type == "bar":
        ax.bar(labels, values)
    elif payload.chart_type == "line":
        ax.plot(labels, values, marker="o")
    else:
        raise ValueError(f"Type de graphique non supporté: {payload.chart_type}")

    ax.set_title(payload.title)
    ax.set_xlabel(payload.x_label)
    ax.set_ylabel(payload.y_label)
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()

    if payload.return_base64:
        buffer = io.BytesIO()
        fig.savefig(buffer, format="png", bbox_inches="tight")
        plt.close(fig)
        buffer.seek(0)
        encoded = base64.b64encode(buffer.read()).decode("utf-8")
        return {
            "status": "success",
            "format": "base64",
            "image_base64": encoded,
        }

    tmp_dir = Path(tempfile.gettempdir())
    output_path = tmp_dir / f"plot_{payload.chart_type}.png"
    fig.savefig(output_path, format="png", bbox_inches="tight")
    plt.close(fig)

    return {
        "status": "success",
        "format": "file",
        "file_path": str(output_path),
    }


class PlotTool(BaseTool):
    name: str = "plot_tool"
    description: str = (
        "Génère un graphique à partir de données structurées. "
        "Entrée attendue au format JSON avec chart_type, title, labels éventuels et data."
    )

    def _run(self, tool_input: str) -> str:
        try:
            raw_payload = json.loads(tool_input)
            payload = PlotToolInput(**raw_payload)
            result = build_plot(payload)
            return json.dumps(result, ensure_ascii=False)
        except json.JSONDecodeError as e:
            return json.dumps(
                {"status": "error", "message": f"Entrée JSON invalide: {e}"},
                ensure_ascii=False,
            )
        except ValidationError as e:
            return json.dumps(
                {"status": "error", "message": f"Validation échouée: {e}"},
                ensure_ascii=False,
            )
        except Exception as e:
            return json.dumps(
                {"status": "error", "message": f"Erreur lors de la génération du graphique: {e}"},
                ensure_ascii=False,
            )