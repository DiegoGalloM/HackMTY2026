import PhoneFrame from "./onboarding/PhoneFrame.jsx";
import Logo from "./onboarding/Logo.jsx";
import Onboarding from "./onboarding/Onboarding.jsx";

export default function App() {
  return (
    <PhoneFrame>
      <Logo />
      <Onboarding />
    </PhoneFrame>
  );
}