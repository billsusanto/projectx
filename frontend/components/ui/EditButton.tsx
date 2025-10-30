'use client';

interface EditButtonProps {
  onEdit: () => void;
  className?: string;
}

const EditButton = ({ onEdit, className = '' }: EditButtonProps) => {
  return (
    <button
      onClick={onEdit}
      className={`px-3 py-1 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-1 transition-colors ${className}`}
      aria-label="Edit todo"
    >
      Edit
    </button>
  );
};

export default EditButton;
