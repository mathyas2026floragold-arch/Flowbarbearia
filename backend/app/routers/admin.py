from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from ..db import session,set_scope
from ..security import Principal,require
from ..schemas import BarbershopIn,PlanIn,RenewIn
from ..services.supabase_admin import create_owner
router=APIRouter(prefix="/api/admin",tags=["admin"])

@router.get("/dashboard")
async def dashboard(p:Principal=Depends(require("superadmin")),db:AsyncSession=Depends(session)):
 await set_scope(db,p.user_id,None,p.role)
 return (await db.execute(text("""select count(*) total,
  count(*) filter(where status='active') active,count(*) filter(where status='trial') trial,
  count(*) filter(where status='suspended') suspended,
  coalesce((select sum(coalesce(monthly_value,pl.monthly_price,pl.price)) from subscriptions s join plans pl on pl.id=s.plan_id where s.status='active'),0) monthly_revenue,
  (select count(*) from appointments) appointments,
  (select count(*) from scheduled_messages where status='sent') messages_sent from barbershops"""))).mappings().one()

@router.get("/barbershops")
async def list_companies(p:Principal=Depends(require("superadmin")),db:AsyncSession=Depends(session)):
 await set_scope(db,p.user_id,None,p.role)
 return (await db.execute(text("""select b.id,b.name,b.slug,b.status,b.created_at,s.expires_at,s.grace_days,
  pl.name plan_name,coalesce(s.monthly_value,pl.monthly_price,pl.price) monthly_value,
  (select count(*) from barbers x where x.barbershop_id=b.id) barbers_count,
  (select count(*) from customers x where x.barbershop_id=b.id) customers_count,
  (select count(*) from appointments x where x.barbershop_id=b.id) appointments_count,
  (select status from whatsapp_connections x where x.barbershop_id=b.id limit 1) whatsapp_status
  from barbershops b left join lateral(select * from subscriptions x where x.barbershop_id=b.id order by x.created_at desc limit 1)s on true
  left join plans pl on pl.id=s.plan_id order by b.created_at desc"""))).mappings().all()

@router.get("/plans")
async def list_plans(p:Principal=Depends(require("superadmin")),db:AsyncSession=Depends(session)):
 await set_scope(db,p.user_id,None,p.role)
 return (await db.execute(text("select id,name,coalesce(monthly_price,price) monthly_price,max_barbers,max_units,limits,features,active from plans order by name"))).mappings().all()

@router.post("/plans",status_code=201)
async def create_plan(data:PlanIn,p:Principal=Depends(require("superadmin")),db:AsyncSession=Depends(session)):
 await set_scope(db,p.user_id,None,p.role)
 row=(await db.execute(text("""insert into plans(name,price,monthly_price,max_barbers,max_units,limits,features)
  values(:n,:p,:p,:b,:u,cast(:l as jsonb),cast(:f as jsonb)) returning *"""),{"n":data.name,"p":data.monthly_price,"b":data.max_barbers,"u":data.max_units,"l":__import__('json').dumps(data.limits),"f":__import__('json').dumps(data.features)})).mappings().one()
 await db.commit();return row

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

@router.post("/barbershops/{company_id}/renew")
async def renew(company_id:str,data:RenewIn,p:Principal=Depends(require("superadmin")),db:AsyncSession=Depends(session)):
 await set_scope(db,p.user_id,None,p.role)
 row=(await db.execute(text("""update subscriptions set expires_at=:e,status='active',last_renewed_at=now(),
  monthly_value=coalesce(:v,monthly_value),notes=coalesce(:n,notes) where id=(select id from subscriptions where barbershop_id=:id order by created_at desc limit 1) returning *"""),{"e":data.expires_at,"v":data.monthly_value,"n":data.notes,"id":company_id})).mappings().one_or_none()
 if not row: raise HTTPException(404,"Assinatura não encontrada")
 await db.execute(text("update barbershops set status='active',updated_at=now() where id=:id"),{"id":company_id})
 await db.execute(text("insert into audit_logs(actor_id,action,entity,entity_id,metadata) values(:a,'subscription.renew','barbershop',:id,jsonb_build_object('expires_at',:e))"),{"a":p.user_id,"id":company_id,"e":data.expires_at})
 await db.commit();return row
