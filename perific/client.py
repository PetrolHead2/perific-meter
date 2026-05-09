import aiohttp
from typing import Optional, List
from pydantic import BaseModel, Field


class Token(BaseModel):
    token: str = Field(alias="Token")
    created: str = Field(alias="Created")
    valid_to: str = Field(alias="ValidTo")


class Item(BaseModel):
    id: int = Field(alias="ItemId")
    name: str = Field(alias="Name")
    system_name: str | None = Field(alias="SystemName")
    item_category: str = Field(alias="ItemCategory")
    item_type: str = Field(alias="ItemType")
    item_sub_type: str = Field(alias="ItemSubType")
    mac_address: str = Field(alias="MacAddress")
    time_zone: str = Field(alias="TimeZone")
    creation_time: str = Field(alias="CreationTime")


class AccountOverviewResponse(BaseModel):
    items: list[Item] = Field(alias="Items")


class ItemPacketData(BaseModel):
    # PhaseRealTime packet fields (firmware 4.x)
    iavg: Optional[List[float]] = Field(default=None, alias="iavg")    # current avg per phase (A)
    imin: Optional[List[float]] = Field(default=None, alias="imin")    # current min per phase (A)
    imax: Optional[List[float]] = Field(default=None, alias="imax")    # current max per phase (A)
    # qmax is a cumulative energy counter per phase (raw units; 1 unit ≈ 0.184 J)
    qmax: Optional[List[int]] = Field(default=None, alias="qmax")


class ItemPacket(BaseModel):
    hdr: int = Field(alias="hdr")
    iid: int = Field(alias="iid")
    ts: int = Field(alias="ts")
    seqno: int = Field(alias="seqno")
    it: str = Field(alias="it")
    pv: int = Field(alias="pv")
    fw: str = Field(alias="fw")
    rssi: int = Field(alias="rssi")
    data: ItemPacketData = Field(alias="data")


class LatestPackets(BaseModel):
    phase_real_time: Optional[ItemPacket] = Field(default=None, alias="PhaseRealTime")


class LatestItemPackets(BaseModel):
    item_id: int = Field(alias="ItemId")
    latest_packets: LatestPackets = Field(alias="LatestPackets")


class Client:

    def __init__(self, host: str):
        self.host = host

    async def authenticate(self, username: str, password: str) -> Token:
        url = f"{self.host}/createtoken"
        async with aiohttp.ClientSession() as session:
            async with session.put(
                url,
                json={"username": username, "password": password},
                headers={"Content-Type": "application/json"},
                timeout=10,
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    token_info = data.get("TokenInfo")
                    if token_info:
                        return Token(**token_info)
                    raise Exception("Invalid response: TokenInfo not found")
                raise Exception(f"Authentication failed: {response.status}")

    async def getLatestPackets(self, token: str) -> list[LatestItemPackets]:
        url = f"{self.host}/getlatestpackets"
        headers = {
            "X-Authorization": token,
            "Content-Type": "application/json",
        }
        async with aiohttp.ClientSession() as session:
            async with session.put(url, headers=headers, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    return [LatestItemPackets(**item) for item in data]
                elif response.status == 401:
                    raise AuthenticationError("Unauthorized access")
                raise Exception(f"Failed to get latest packets: {response.status}")

    async def getAccountOverview(self, token: str) -> AccountOverviewResponse:
        url = f"{self.host}/getaccountoverview"
        headers = {
            "X-Authorization": token,
            "Content-Type": "application/json",
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    return AccountOverviewResponse(**data)
                elif response.status == 401:
                    raise AuthenticationError("Unauthorized access")
                raise Exception(f"Failed to get account overview: {response.status}")

    async def getReporterSettings(self, token: str) -> dict | None:
        url = f"{self.host}/getreporterssettingsforuser"
        headers = {
            "X-Authorization": token,
            "Content-Type": "application/json",
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    reporters = data.get("ZaptecReporters", [])
                    if not reporters:
                        return None
                    first = reporters[0]
                    settings: dict = {}
                    settings.update(first.get("SimpleSettings", {}))
                    settings.update(first.get("UserSettings", {}))
                    return settings
                elif response.status == 401:
                    raise AuthenticationError("Unauthorized access")
                raise Exception(f"Failed to get reporter settings: {response.status}")


class AuthenticationError(Exception):
    """Custom exception for authentication errors."""
    pass
