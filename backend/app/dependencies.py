from fastapi import Depends,HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from .db import session,set_scope
from .security import Principal,principal
async def scoped_db(p:Principal=Depends(principal),s:AsyncSession=Depends(session)):
 await set_scope(s,p.user_id,p.barbershop_id,p.role)
 if p.role!="superadmin":
  allowed=await s.scalar(text("select barbershop_has_access(:id)"),{"id":p.barbershop_id})
  if not allowed: raise HTTPException(403,"Assinatura vencida ou barbearia suspensa")
 return s
