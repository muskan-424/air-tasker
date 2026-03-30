from pydantic import BaseModel, Field


class NotificationOut(BaseModel):
    id: str
    title: str
    body: str
    category: str
    read_at: str | None
    delivery_status: str
    created_at: str

    model_config = {"from_attributes": False}


class NotificationPrefsUpdate(BaseModel):
    in_app_enabled: bool | None = None
    email_enabled: bool | None = None
    email_task: bool | None = None
    email_escrow: bool | None = None
    email_dispute: bool | None = None


class NotificationPrefsOut(BaseModel):
    in_app_enabled: bool
    email_enabled: bool
    email_task: bool
    email_escrow: bool
    email_dispute: bool
