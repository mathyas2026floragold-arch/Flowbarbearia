from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from ..db import session
from ..schemas import AppointmentIn,WaitingListIn
router=APIRouter(prefix="/api/public",tags=["public"])

@router.get("/{slug}/services")
async def services(slug:str,db:AsyncSession=Depends(session)):
 return (await db.execute(text("select s.id,s.name,s.duration_minutes,s.buffer_minutes,s.price,s.return_days from services s join barbershops b on b.id=s.barbershop_id where b.slug=:slug and barbershop_has_access(b.id) and s.active and s.public"),{"slug":slug})).mappings().all()

@router.get("/{slug}/barbers")
async def barbers(slug:str,service_id:str|None=None,db:AsyncSession=Depends(session)):
 return (await db.execute(text("""select distinct br.id,br.display_name from barbers br join barbershops b on b.id=br.barbershop_id
  left join barber_services bs on bs.barber_id=br.id where b.slug=:slug and barbershop_has_access(b.id)
  and br.active and br.public and (:service is null or bs.service_id=cast(:service as uuid)) order by br.display_name"""),{"slug":slug,"service":service_id})).mappings().all()

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

@router.post("/{slug}/waiting-list",status_code=201)
async def join_waiting_list(slug:str,data:WaitingListIn,db:AsyncSession=Depends(session)):
 row=(await db.execute(text("""insert into waiting_list(barbershop_id,customer_name,phone_e164,service_id,barber_id,desired_day,time_from,time_to)
  select b.id,:name,:phone,:service,:barber,:day,cast(:from as time),cast(:to as time) from barbershops b
  where b.slug=:slug and b.status in('trial','active') returning *"""),{"name":data.customer_name,"phone":data.customer_phone,"service":data.service_id,"barber":data.barber_id,"day":data.desired_day,"from":data.time_from,"to":data.time_to,"slug":slug})).mappings().one_or_none()
 if not row: raise HTTPException(404,"Barbearia indisponível")
 await db.commit();return row
