from google import genai
from google.genai import types
from ..config import get_settings
TOOLS=[types.Tool(function_declarations=[types.FunctionDeclaration(name="list_services",description="Lista serviços reais da barbearia",parameters={"type":"OBJECT","properties":{}}),types.FunctionDeclaration(name="check_availability",description="Consulta horários reais",parameters={"type":"OBJECT","properties":{"service_id":{"type":"STRING"},"date":{"type":"STRING"}},"required":["service_id","date"]}),types.FunctionDeclaration(name="create_appointment",description="Cria agendamento após confirmação explícita",parameters={"type":"OBJECT","properties":{"service_id":{"type":"STRING"},"starts_at":{"type":"STRING"}},"required":["service_id","starts_at"]})])]
async def next_action(message:str,context:str):
 s=get_settings();client=genai.Client(api_key=s.gemini_api_key)
 prompt=f"Você atende uma barbearia. Nunca invente preço, horário ou política; use funções. Nunca marque presença ou conclusão. Contexto: {context}\nCliente: {message}"
 return await client.aio.models.generate_content(model=s.gemini_model,contents=prompt,config=types.GenerateContentConfig(tools=TOOLS,temperature=0.2))
