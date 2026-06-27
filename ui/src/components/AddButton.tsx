interface AddButtonProps {
  text: string;
  onClick: () => void;
}

const AddButton: React.FC<AddButtonProps> = ({ text, onClick }) => (
  <button
    onClick={onClick}
    className="px-4 py-2 text-white rounded-md bg-emd-accent text-emd-buttonText font-semibold hover:bg-emd-primary transition-colors duration-200 cursor-pointer"
  >
    {text}
  </button>
);
export default AddButton;
