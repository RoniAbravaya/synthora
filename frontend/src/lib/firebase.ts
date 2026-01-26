/**
 * Firebase Configuration and Authentication
 * 
 * Initializes Firebase app and provides authentication utilities.
 * Also provides social platform OAuth flows using Firebase's Google provider.
 */

import { initializeApp } from "firebase/app"
import {
  getAuth,
  GoogleAuthProvider,
  signInWithPopup,
  signOut as firebaseSignOut,
  onAuthStateChanged,
  type User as FirebaseUser,
  type OAuthCredential,
} from "firebase/auth"

// Firebase configuration from environment variables
const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
  appId: import.meta.env.VITE_FIREBASE_APP_ID,
}

// Initialize Firebase
const app = initializeApp(firebaseConfig)
const auth = getAuth(app)

// Google Auth Provider (basic - for app sign-in)
const googleProvider = new GoogleAuthProvider()
googleProvider.addScope("email")
googleProvider.addScope("profile")

/**
 * Sign in with Google popup.
 */
export async function signInWithGoogle(): Promise<FirebaseUser> {
  const result = await signInWithPopup(auth, googleProvider)
  return result.user
}

// =============================================================================
// Social Platform OAuth via Firebase
// =============================================================================

/**
 * YouTube OAuth scopes for uploading and managing videos.
 */
const YOUTUBE_SCOPES = [
  "https://www.googleapis.com/auth/youtube.upload",
  "https://www.googleapis.com/auth/youtube.readonly",
  "https://www.googleapis.com/auth/youtube.force-ssl",
]

/**
 * Result of a social platform OAuth flow.
 */
export interface SocialOAuthResult {
  accessToken: string
  providerId: string
  platformUserId: string | null
  email: string | null
  displayName: string | null
  photoUrl: string | null
}

/**
 * Connect YouTube account using Firebase Google OAuth.
 * Opens a popup for the user to authorize YouTube access.
 * 
 * @returns OAuth result with access token for YouTube API
 */
export async function connectYouTubeAccount(): Promise<SocialOAuthResult> {
  // Create a new provider with YouTube scopes
  const youtubeProvider = new GoogleAuthProvider()
  youtubeProvider.addScope("email")
  youtubeProvider.addScope("profile")
  
  // Add YouTube-specific scopes
  for (const scope of YOUTUBE_SCOPES) {
    youtubeProvider.addScope(scope)
  }
  
  // Force account selection even if already signed in
  youtubeProvider.setCustomParameters({
    prompt: "consent",
    access_type: "offline",
  })
  
  try {
    const result = await signInWithPopup(auth, youtubeProvider)
    
    // Get the Google OAuth credential with access token
    const credential = GoogleAuthProvider.credentialFromResult(result)
    
    if (!credential || !credential.accessToken) {
      throw new Error("Failed to get access token from Google")
    }
    
    const user = result.user
    
    return {
      accessToken: credential.accessToken,
      providerId: "google.com",
      platformUserId: user.providerData[0]?.uid || user.uid,
      email: user.email,
      displayName: user.displayName,
      photoUrl: user.photoURL,
    }
  } catch (error: any) {
    // Handle specific Firebase auth errors
    if (error.code === "auth/popup-closed-by-user") {
      throw new Error("Sign-in popup was closed. Please try again.")
    }
    if (error.code === "auth/cancelled-popup-request") {
      throw new Error("Sign-in was cancelled. Please try again.")
    }
    if (error.code === "auth/popup-blocked") {
      throw new Error("Popup was blocked by browser. Please allow popups for this site.")
    }
    throw error
  }
}

/**
 * Sign out the current user.
 */
export async function signOut(): Promise<void> {
  await firebaseSignOut(auth)
}

/**
 * Get the current user's ID token.
 */
export async function getIdToken(): Promise<string | null> {
  const user = auth.currentUser
  if (!user) return null
  return user.getIdToken()
}

/**
 * Subscribe to auth state changes.
 */
export function onAuthChange(callback: (user: FirebaseUser | null) => void): () => void {
  return onAuthStateChanged(auth, callback)
}

/**
 * Get the current Firebase user.
 */
export function getCurrentUser(): FirebaseUser | null {
  return auth.currentUser
}

export { auth, type FirebaseUser }

