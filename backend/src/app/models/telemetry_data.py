from __future__ import annotations
from typing import Dict, Optional

import pandas as pd
from pydantic import BaseModel, ConfigDict


class TelemetryData(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    """Holds one DataFrame per MAVLink message type."""
    by_type: Dict[str, pd.DataFrame]

    # ------------- helpers -------------
    def get_df(self, mtype: str) -> Optional[pd.DataFrame]:
        return self.by_type.get(mtype)
