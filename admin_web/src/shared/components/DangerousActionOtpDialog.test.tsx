import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { DangerousActionOtpDialog } from "./DangerousActionOtpDialog";

const labels = {
  cancel: "Cancel",
  loading: "Loading",
  otp: "OTP code",
  verify: "Verify",
};

describe("DangerousActionOtpDialog", () => {
  it("collects OTP and confirms destructive action", () => {
    const onOtpChange = vi.fn();
    const onCancel = vi.fn();
    const onConfirm = vi.fn();

    render(
      <DangerousActionOtpDialog
        t={labels}
        open
        title="Delete all"
        text="Enter OTP"
        otp="123456"
        devOtpHint="111111"
        error="Invalid OTP"
        pending={false}
        onOtpChange={onOtpChange}
        onCancel={onCancel}
        onConfirm={onConfirm}
      />,
    );

    fireEvent.change(screen.getByLabelText("OTP code"), { target: { value: "654321" } });
    fireEvent.click(screen.getByText("Verify"));
    fireEvent.click(screen.getByText("Cancel"));

    expect(screen.getByText("Delete all")).toBeInTheDocument();
    expect(screen.getByText("Dev OTP: 111111")).toBeInTheDocument();
    expect(screen.getByText("Invalid OTP")).toBeInTheDocument();
    expect(onOtpChange).toHaveBeenCalledWith("654321");
    expect(onConfirm).toHaveBeenCalledTimes(1);
    expect(onCancel).toHaveBeenCalledTimes(1);
  });

  it("blocks confirmation while pending or OTP is too short", () => {
    const onConfirm = vi.fn();
    const { rerender } = render(
      <DangerousActionOtpDialog
        t={labels}
        open
        title="Delete all"
        text="Enter OTP"
        otp="123"
        pending={false}
        onOtpChange={vi.fn()}
        onCancel={vi.fn()}
        onConfirm={onConfirm}
      />,
    );

    expect(screen.getByText("Verify")).toBeDisabled();

    rerender(
      <DangerousActionOtpDialog
        t={labels}
        open
        title="Delete all"
        text="Enter OTP"
        otp="123456"
        pending
        onOtpChange={vi.fn()}
        onCancel={vi.fn()}
        onConfirm={onConfirm}
      />,
    );

    expect(screen.getByText("Loading")).toBeDisabled();
  });

  it("uses fallback cancel label", () => {
    render(
      <DangerousActionOtpDialog
        t={{ loading: "Loading", otp: "OTP code", verify: "Verify" }}
        open
        title="Delete all"
        text="Enter OTP"
        otp="123456"
        pending={false}
        onOtpChange={vi.fn()}
        onCancel={vi.fn()}
        onConfirm={vi.fn()}
      />,
    );

    expect(screen.getByText("Cancel")).toBeInTheDocument();
  });
});
