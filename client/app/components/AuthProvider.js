'use client';

import { createContext, useContext, useEffect, useState } from 'react';
import { onAuthStateChanged, signOut } from 'firebase/auth';
import { auth } from '../lib/firebase';

const AuthContext = createContext({});

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (user) => {
      if (user) {
        // Validate that the user has a valid token
        try {
          await user.getIdToken(true); // Force refresh token
          console.log('✅ Valid Firebase session detected');
          setUser(user);
        } catch (error) {
          console.error('❌ Invalid session detected, forcing logout:', error);
          // Invalid token - clear everything and force re-login
          try {
            await signOut(auth);
            localStorage.clear();
            sessionStorage.clear();
          } catch (e) {
            console.error('Error during forced logout:', e);
          }
          setUser(null);
        }
      } else {
        setUser(null);
      }
      setLoading(false);
    });

    return unsubscribe;
  }, []);

  // Periodic token validation check (every 5 minutes)
  useEffect(() => {
    if (!user) return;

    const validateToken = async () => {
      try {
        await user.getIdToken(true);
        console.log('✅ Token validated');
      } catch (error) {
        console.error('❌ Token validation failed, forcing logout');
        await logout();
        window.location.href = '/auth/login';
      }
    };

    const interval = setInterval(validateToken, 5 * 60 * 1000); // Every 5 minutes
    return () => clearInterval(interval);
  }, [user]);

  const logout = async () => {
    try {
      await signOut(auth);
      localStorage.clear();
      sessionStorage.clear();
    } catch (error) {
      console.error('Logout error:', error);
    }
  };

  return (
    <AuthContext.Provider value={{ user, loading, logout }}>
      {children}
    </AuthContext.Provider>
  );
};
