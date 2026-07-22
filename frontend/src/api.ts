import { createClient } from "@supabase/supabase-js";

const configuredSupabaseUrl=String(import.meta.env.VITE_SUPABASE_URL||"").trim();
const configuredAnonKey=String(import.meta.env.VITE_SUPABASE_ANON_KEY||"").trim();
const configuredApiUrl=String(import.meta.env.VITE_API_URL||"").trim().replace(/\/$/,"");

export const configurationError=!configuredSupabaseUrl||!configuredAnonKey||!configuredApiUrl
 ? "A publicação ainda não recebeu VITE_SUPABASE_URL, VITE_SUPABASE_ANON_KEY e VITE_API_URL."
 : "";

// Os valores neutros evitam tela branca e deixam a interface explicar a configuração ausente.
export const supabase=createClient(
 configuredSupabaseUrl||"https://configuracao-ausente.supabase.co",
 configuredAnonKey||"configuracao-ausente",
);

export async function api<T>(path:string,init:RequestInit={}){
 if(configurationError) throw new Error(configurationError);
 const {data}=await supabase.auth.getSession();
 const headers=new Headers(init.headers);
 headers.set("Content-Type","application/json");
 if(data.session) headers.set("Authorization",`Bearer ${data.session.access_token}`);
 const res=await fetch(`${configuredApiUrl}${path}`,{...init,headers});
 if(!res.ok){
  const body=await res.json().catch(()=>({detail:`Backend indisponível (HTTP ${res.status})`}));
  throw new Error(typeof body.detail==="string"?body.detail:`Backend indisponível (HTTP ${res.status})`);
 }
 return res.status===204?undefined as T:res.json() as Promise<T>;
}
