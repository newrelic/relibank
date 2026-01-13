export interface UserAccount {
  account_type: 'checking' | 'savings';
  balance: number;
  routing_number: string;
}

export interface UserData {
  id?: string;
  name: string;
  email?: string;
  avatar?: string;
  // userData can be array of accounts OR object with accounts array
  [key: string]: any;
}

export interface LoginContextType {
  isAuthenticated: boolean;
  handleLogin: (data: any) => void;
  handleLogout: () => void;
  userData: any;
  setUserData: (data: any) => void;
}
