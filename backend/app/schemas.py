from datetime import datetime,date
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
class PlanIn(BaseModel):
 name:str=Field(min_length=2,max_length=80)
 monthly_price:Decimal=Field(ge=0)
 max_barbers:int|None=Field(default=None,ge=1)
 max_units:int=Field(default=1,ge=1)
 limits:dict=Field(default_factory=dict)
 features:dict=Field(default_factory=dict)
class RenewIn(BaseModel):
 expires_at:datetime
 monthly_value:Decimal|None=Field(default=None,ge=0)
 notes:str|None=None
class BarberIn(BaseModel):
 display_name:str=Field(min_length=2,max_length=100)
 active:bool=True
 public:bool=True
class WaitingListIn(BaseModel):
 service_id:UUID
 barber_id:UUID|None=None
 desired_day:date
 time_from:str|None=None
 time_to:str|None=None
 customer_name:str=Field(min_length=2,max_length=120)
 customer_phone:str=Field(pattern=r"^\+[1-9]\d{7,14}$")
class AISettingsIn(BaseModel):
 assistant_name:str=Field(min_length=2,max_length=60)
 tone:str=Field(min_length=2,max_length=40)
 instructions:str=Field(max_length=4000,default="")
 enabled:bool=True
