from __future__ import annotations

import ipaddress
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class TargetCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=2, max_length=80)
    host: str = Field(min_length=1, max_length=253)
    check_type: Literal["tcp", "dns"] = "tcp"
    port: int | None = Field(default=None, ge=1, le=65535)

    @field_validator("host")
    @classmethod
    def validate_host(cls, value: str) -> str:
        value = value.strip().rstrip(".")
        if not value or "://" in value or "/" in value or any(c.isspace() for c in value):
            raise ValueError("Enter a hostname or IP address, not a URL.")
        try:
            ipaddress.ip_address(value)
            return value
        except ValueError:
            pass

        if len(value) > 253:
            raise ValueError("Hostname is too long.")
        labels = value.split(".")
        valid = all(
            1 <= len(label) <= 63
            and re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?", label)
            for label in labels
        )
        if not valid:
            raise ValueError("Enter a valid DNS hostname or IP address.")
        return value.lower()

    @model_validator(mode="after")
    def validate_port(self):
        if self.check_type == "tcp" and self.port is None:
            raise ValueError("TCP checks require a port.")
        if self.check_type == "dns" and self.port is not None:
            raise ValueError("DNS checks do not use a port.")
        return self
