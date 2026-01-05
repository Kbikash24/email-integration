import { auth as firebaseAuth } from '../../app/lib/firebase';

export const auth = firebaseAuth;

export const getIdToken = async () => {
  const user = auth.currentUser;
  if (!user) throw new Error('No authenticated user');
  return await user.getIdToken();
};
