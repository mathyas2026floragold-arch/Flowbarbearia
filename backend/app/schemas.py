from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel,Field
from uuid import UUID
class ServiceIn(BaseModel):
 name:str=Field(min_length=2,max_length=100)
 duration_minutes:int=Field(gt=0,le=480)
 buffer_minutes:int=Field(ge=0,le=120,default=0)
 price:Decimal=Field(ge=0)
 return_days:int=Field(ge=1,le=365,default=28)
class AppointmentIn(BaseModel):
 service_id:UUID
 barber_id:UUID|None=None
 starts_at:datetime
 customer_name:str=Field(min_length=2,max_length=120)
 customer_phone:str=Field(pattern=r"^\+[1-9]\d{7,14}$")
class StatusIn(BaseModel): status:str
class BarbershopIn(BaseModel):
 name:str
 slug:str
 owner_email:str
 plan_id:UUID
 expires_at:datetime
