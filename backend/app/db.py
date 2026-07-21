from sqlalchemy.ext.asyncio import create_async_engine,async_sessionmaker,AsyncSession
from sqlalchemy import text
from .config import get_settings

engine=create_async_engine(get_settings().database_url,pool_pre_ping=True)
Session=async_sessionmaker(engine,expire_on_commit=False)
async def session():
 async with Session() as s: yield s
async def set_scope(s:AsyncSession,user_id:str,barbershop_id:str|None,role:str):
 await s.execute(text("select set_config('app.user_id', :u, true), set_config('app.barbershop_id', :b, true), set_config('app.role', :r, true)"),{"u":user_id,"b":barbershop_id or "","r":role})
