export function homeForRole(role:string){
 return role==="superadmin"?"/admin":role==="barber"?"/barber":"/app";
}

export function normalizePhoneE164(value:string){
 const trimmed=value.trim();
 if(/^\+[1-9]\d{7,14}$/.test(trimmed)) return trimmed;
 const digits=trimmed.replace(/\D/g,"");
 if(/^55\d{10,11}$/.test(digits)) return `+${digits}`;
 if(/^\d{10,11}$/.test(digits)) return `+55${digits}`;
 return null;
}

export function money(value:number){
 return new Intl.NumberFormat("pt-BR",{style:"currency",currency:"BRL"}).format(value);
}
