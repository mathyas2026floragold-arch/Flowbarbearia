import { createClient } from "@supabase/supabase-js";
export const supabase=createClient(import.meta.env.VITE_SUPABASE_URL,import.meta.env.VITE_SUPABASE_ANON_KEY);
const base=import.meta.env.VITE_API_URL;
export async function api<T>(path:string,init:RequestInit={}){
 const {data}=await supabase.auth.getSession();
 const headers=new Headers(init.headers); headers.set("Content-Type","application/json");
 if(data.session) headers.set("Authorization",`Bearer ${data.session.access_token}`);
 const res=await fetch(`${base}${path}`,{...init,headers});
 if(!res.ok) throw new Error((await res.json().catch(()=>({detail:"Erro de comunicação"}))).detail);
 return res.status===204?undefined as T:res.json() as Promise<T>;
}
