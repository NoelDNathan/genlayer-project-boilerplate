"use client";

import React, { createContext, useContext, useState, useEffect } from "react";
import { createAccount, getAccount, removeAccount, type Account } from "./genlayer";

interface AccountContextType {
  account: Account | null;
  connectAccount: () => Account;
  disconnectAccount: () => void;
  accountAddress: string | null;
  balance: number;
  updateBalance: (amount: number) => void;
  subtractBalance: (amount: number) => void;
  addBalance: (amount: number) => void;
}

const AccountContext = createContext<AccountContextType | undefined>(undefined);

export function AccountProvider({ children }: { children: React.ReactNode }) {
  const [account, setAccount] = useState<Account | null>(null);
  const [balance, setBalance] = useState<number>(2000); // Default balance

  useEffect(() => {
    const savedAccount = getAccount();
    setAccount(savedAccount);
    // Load balance from localStorage if exists
    const savedBalance = localStorage.getItem("playerBalance");
    if (savedBalance) {
      setBalance(Number(savedBalance));
    }
  }, []);

  const connectAccount = () => {
    const newAccount = createAccount();
    setAccount(newAccount);
    // Reset balance when connecting new account
    setBalance(2000);
    localStorage.setItem("playerBalance", "2000");
    return newAccount;
  };

  const disconnectAccount = () => {
    removeAccount();
    setAccount(null);
    // Reset balance when disconnecting
    setBalance(2000);
    localStorage.setItem("playerBalance", "2000");
  };

  const updateBalance = (amount: number) => {
    setBalance(amount);
    localStorage.setItem("playerBalance", amount.toString());
  };

  const subtractBalance = (amount: number) => {
    const newBalance = Math.max(0, balance - amount);
    setBalance(newBalance);
    localStorage.setItem("playerBalance", newBalance.toString());
  };

  const addBalance = (amount: number) => {
    const newBalance = balance + amount;
    setBalance(newBalance);
    localStorage.setItem("playerBalance", newBalance.toString());
  };

  // Get account address - try multiple ways to access it
  const getAccountAddress = (): string | null => {
    if (!account) return null;
    
    try {
      // Method 1: Direct property access
      if ((account as any).address) {
        const addr = (account as any).address;
        if (typeof addr === 'string' && addr.length === 42 && addr.startsWith('0x')) {
          return addr;
        }
        if (typeof addr === 'function') {
          const addrResult = addr();
          if (typeof addrResult === 'string' && addrResult.length === 42 && addrResult.startsWith('0x')) {
            return addrResult;
          }
        }
      }
      
      // Method 2: Try to get from account object properties
      const accountAny = account as any;
      if (accountAny.getAddress && typeof accountAny.getAddress === 'function') {
        const addr = accountAny.getAddress();
        if (typeof addr === 'string' && addr.length === 42 && addr.startsWith('0x')) {
          return addr;
        }
      }
      
      // Method 3: The address might be available but we can't access it directly
      // In this case, return null and let the client handle it
      // The client will derive the address from the account when needed
      return null;
    } catch (error) {
      console.error('Error getting account address:', error);
      return null;
    }
  };
  
  const accountAddress = getAccountAddress();

  return (
    <AccountContext.Provider
      value={{
        account,
        connectAccount,
        disconnectAccount,
        accountAddress,
        balance,
        updateBalance,
        subtractBalance,
        addBalance,
      }}
    >
      {children}
    </AccountContext.Provider>
  );
}

export function useAccount() {
  const context = useContext(AccountContext);
  if (context === undefined) {
    throw new Error("useAccount must be used within an AccountProvider");
  }
  return context;
}

