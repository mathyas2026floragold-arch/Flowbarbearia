from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from ..db import session
from ..schemas import AppointmentIn
router=APIRouter(prefix="/api/public",tags=["public"])

@router.get("/{slug}/services")
async def services(slug:str,db:AsyncSession=Depends(session)):
 return (await db.execute(text("select s.id,s.name,s.duration_minutes,s.buffer_minutes,s.price,s.return_days from services s join barbershops b on b.id=s.barbershop_id where b.slug=:slug and b.status in ('trial','active') and s.active and s.public"),{"slug":slug})).mappings().all()

@router.get("/{slug}/availability")
async def availability(slug:str,service_id:str,day:str,barber_id:str|None=None,db:AsyncSession=Depends(session)):
 return (await db.execute(text("select * from public_available_slots(:slug,:service,cast(:day as date),:barber)"),{"slug":slug,"service":service_id,"day":day,"barber":barber_id})).mappings().all()

@router.post("/{slug}/appointments",status_code=201)
async def book(slug:str,data:AppointmentIn,db:AsyncSession=Depends(session)):
 try:
  row=(await db.execute(text("select * from public_create_appointment(:slug,:service,:barber,:starts,:name,:phone)"),{"slug":slug,"service":data.service_id,"barber":data.barber_id,"starts":data.starts_at,"name":data.customer_name,"phone":data.customer_phone})).mappings().one()
  await db.commit()
  return row
 except Exception as e:
  await db.rollback()
  raise HTTPException(409,"Horário indisponível; escolha outro") from e
