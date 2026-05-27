import { adminApi } from "../../../api/adminApi";

export type AdminActionOtpRequest = {
  action_key: string;
};

export function requestAdminActionOtp(payload: AdminActionOtpRequest) {
  return adminApi("/auth/action-otp", { method: "POST", body: JSON.stringify(payload) });
}

