"""Build typed ``*_info`` DataFrames from engine rows."""

from __future__ import annotations

import pandas as pd

from pyrfs._engine.fileops import INFO_COLUMNS

__all__ = ["info_frame"]

_TIME_COLUMNS = ("modification_time", "access_time", "change_time", "birth_time")


def info_frame(rows: list[dict[str, object]]) -> pd.DataFrame:
    """Turn engine info rows into a DataFrame with pyrfs-typed columns."""
    df = pd.DataFrame(rows, columns=list(INFO_COLUMNS))
    df["path"] = df["path"].astype("path")
    df["size"] = df["size"].astype("bytes")
    df["permissions"] = df["permissions"].astype("perms")
    for column in _TIME_COLUMNS:
        df[column] = pd.to_datetime(df[column])
    return df
