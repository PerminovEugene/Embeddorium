interface RemoveButtonProps {
  text: string;
  onClick: () => void;
}

const RemoveButton: React.FC<RemoveButtonProps> = ({ text, onClick }) => (
  <button
    onClick={onClick}
    className="px-4 py-2 text-white rounded-md bg-red-400 text-emd-buttonText font-semibold hover:bg-red-500 transition-colors duration-200 cursor-pointer"
  >
    {text}
  </button>
);
export default RemoveButton;
