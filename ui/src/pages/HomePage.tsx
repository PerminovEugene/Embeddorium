import CompareComponent from "../components/CompareComponent";
import { FormProvider } from "../components/FormContext";

const HomePage = () => {
  return (
    <FormProvider>
      <CompareComponent />
    </FormProvider>
  );
};

export default HomePage;
