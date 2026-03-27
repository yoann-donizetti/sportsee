"""Schémas Pydantic pour valider les données avant insertion en base."""

from typing import Optional

from pydantic import BaseModel, Field


class TeamRecord(BaseModel):
    """Représente une équipe NBA."""
    team_code: str = Field(..., min_length=2, max_length=10)
    team_name: str = Field(..., min_length=2)


class PlayerRecord(BaseModel):
    """Représente un joueur NBA."""
    player_name: str = Field(..., min_length=2)
    team_code: str = Field(..., min_length=2, max_length=10)
    age: Optional[int] = Field(default=None, ge=15, le=60)


class StatRecord(BaseModel):
    """Représente les statistiques agrégées d’un joueur."""

    player_name: str = Field(..., min_length=2)

    gp: Optional[int] = None
    w: Optional[int] = None
    l: Optional[int] = None
    minutes_avg: Optional[float] = None

    pts: Optional[float] = None

    fgm: Optional[float] = None
    fga: Optional[float] = None
    fg_pct: Optional[float] = None

    fifteen_min: Optional[float] = None

    fg3a: Optional[float] = None
    fg3_pct: Optional[float] = None

    ftm: Optional[float] = None
    fta: Optional[float] = None
    ft_pct: Optional[float] = None

    oreb: Optional[float] = None
    dreb: Optional[float] = None
    reb: Optional[float] = None

    ast: Optional[float] = None
    tov: Optional[float] = None
    stl: Optional[float] = None
    blk: Optional[float] = None

    pf: Optional[float] = None
    fp: Optional[float] = None
    dd2: Optional[int] = None
    td3: Optional[int] = None

    plus_minus: Optional[float] = None

    offrtg: Optional[float] = None
    defrtg: Optional[float] = None
    netrtg: Optional[float] = None

    ast_pct: Optional[float] = None
    ast_to: Optional[float] = None
    ast_ratio: Optional[float] = None

    oreb_pct: Optional[float] = None
    dreb_pct: Optional[float] = None
    reb_pct: Optional[float] = None

    to_ratio: Optional[float] = None
    efg_pct: Optional[float] = None
    ts_pct: Optional[float] = None
    usg_pct: Optional[float] = None
    pace: Optional[float] = None
    pie: Optional[float] = None
    poss: Optional[float] = None