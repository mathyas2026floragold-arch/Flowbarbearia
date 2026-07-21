from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from ..db import session,set_scope
from ..security import Principal,require
from ..schemas import BarbershopIn
from ..services.supabase_admin import create_owner
router=APIRouter(prefix="/api/admin",tags=["admin"])

@router.post("/barbershops",status_code=201)
async def create_company(data:BarbershopIn,p:Principal=Depends(require("superadmin")),db:AsyncSession=Depends(session)):
 await set_scope(db,p.user_id,None,p.role)
 row=(await db.execute(text("select * from admin_create_barbershop(:name,:slug,:email,:plan,:expires,:actor)"),{"name":data.name,"slug":data.slug,"email":data.owner_email,"plan":data.plan_id,"expires":data.expires_at,"actor":p.user_id})).mappings().one()
 await db.commit()
 try:
  await create_owner(data.owner_email,str(row["id"]))
 except Exception:
  await db.execute(text("update barbershops set status='suspended' where id=:id"),{"id":row["id"]})
  await db.commit()
  raise HTTPException(502,"Empresa criada suspensa: falha ao provisionar proprietário")
 return row

@router.patch("/barbershops/{company_id}/status")
async def status(company_id:str,state:str,p:Principal=Depends(require("superadmin")),db:AsyncSession=Depends(session)):
 if state not in {"active","suspended","cancelled"}: raise HTTPException(422,"Status inválido")
 await set_scope(db,p.user_id,None,p.role)
 await db.execute(text("update barbershops set status=:s,updated_at=now() where id=:id"),{"s":state,"id":company_id})
 await db.execute(text("insert into audit_logs(actor_id,action,entity,entity_id,metadata) values(:a,'barbershop.status','barbershop',:id,jsonb_build_object('status',:s))"),{"a":p.user_id,"id":company_id,"s":state})
 await db.commit()
 return {"status":state}
