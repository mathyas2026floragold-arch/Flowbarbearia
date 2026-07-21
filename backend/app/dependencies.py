from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from .db import session,set_scope
from .security import Principal,principal
async def scoped_db(p:Principal=Depends(principal),s:AsyncSession=Depends(session)):
 await set_scope(s,p.user_id,p.barbershop_id,p.role)
 return s
