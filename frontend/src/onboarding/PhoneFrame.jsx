// frontend/src/onboarding/PhoneFrame.jsx
export default function PhoneFrame({ children }) {
  return (
    <div className="phone-frame-backdrop">
      <div className="phone-frame">
        <div className="phone-frame__notch" />
        <div className="phone-frame__screen">{children}</div>
        <div className="phone-frame__home-indicator" />
      </div>
    </div>
  );
}