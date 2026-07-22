import {describe,expect,it} from "vitest";
import {homeForRole,normalizePhoneE164} from "./utils";

describe("navegação por perfil",()=>{
 it("separa os três ambientes",()=>{
  expect(homeForRole("superadmin")).toBe("/admin");
  expect(homeForRole("barber")).toBe("/barber");
  expect(homeForRole("owner")).toBe("/app");
 });
});

describe("WhatsApp em formato E.164",()=>{
 it("normaliza telefone brasileiro",()=>{
  expect(normalizePhoneE164("(84) 99999-9999")).toBe("+5584999999999");
  expect(normalizePhoneE164("5584999999999")).toBe("+5584999999999");
 });
 it("rejeita número incompleto",()=>expect(normalizePhoneE164("1234")).toBeNull());
});
