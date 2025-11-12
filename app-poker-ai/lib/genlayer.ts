"use client";

import { createClient, createAccount as createGenLayerAccount, generatePrivateKey } from "genlayer-js";
import { studionet } from "genlayer-js/chains";

export type Account = ReturnType<typeof createGenLayerAccount>;

export function getAccount(): Account | null {
  if (typeof window === "undefined") return null;
  
  const accountPrivateKey = localStorage.getItem("accountPrivateKey");
  return accountPrivateKey ? createGenLayerAccount(accountPrivateKey as `0x${string}`) : null;
}

export function createAccount(): Account {
  if (typeof window === "undefined") {
    throw new Error("Cannot create account on server side");
  }
  
  const newAccountPrivateKey = generatePrivateKey();
  localStorage.setItem("accountPrivateKey", newAccountPrivateKey);
  return createGenLayerAccount(newAccountPrivateKey);
}

export function removeAccount(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem("accountPrivateKey");
}

export function getClient(account: Account | null = null, studioUrl?: string) {
  const config: any = {
    chain: studionet,
    ...(account ? { account } : {}),
  };
  
  // Ensure account is properly set if provided
  if (account && !config.account) {
    config.account = account;
  }
  
  const client = createClient(config);
  return client;
}

