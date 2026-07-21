from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from ..dependencies import scoped_db
from ..security import Principal,require
from ..schemas import ServiceIn,StatusIn
router=APIRouter(prefix="/api/app",tags=["barbershop"])

@router.get("/services")
async def services(p:Principal=Depends(require("owner","manager","barber","receptionist")),db:AsyncSession=Depends(scoped_db)):
 return (await db.execute(text("select id,name,duration_minutes,buffer_minutes,price,return_days from services where active order by name"))).mappings().all()

@router.post("/services",status_code=201)
async def create_service(data:ServiceIn,p:Principal=Depends(require("owner","manager")),db:AsyncSession=Depends(scoped_db)):
 row=(await db.execute(text("insert into services(barbershop_id,name,duration_minutes,buffer_minutes,price,return_days) values(current_setting('app.barbershop_id')::uuid,:n,:d,:b,:p,:r) returning *"),{"n":data.name,"d":data.duration_minutes,"b":data.buffer_minutes,"p":data.price,"r":data.return_days})).mappings().one()
 await db.commit()
 return row

@router.patch("/appointments/{appointment_id}/status")
async def set_status(appointment_id:str,data:StatusIn,p:Principal=Depends(require("owner","manager","barber","receptionist")),db:AsyncSession=Depends(scoped_db)):
 if data.status not in {"confirmed","arrived","in_service","completed","cancelled","no_show"}: raise HTTPException(422,"Transição inválida")
 row=(await db.execute(text("select * from complete_or_update_appointment(:id,:status,:actor)"),{"id":appointment_id,"status":data.status,"actor":p.user_id})).mappings().one_or_none()
 if not row: raise HTTPException(404,"Agendamento não encontrado")
 await db.commit()
 return row
