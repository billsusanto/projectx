'use client';

import React, { useState } from 'react';
import toast from 'react-hot-toast';
import { deleteTodo } from '@/lib/api';

interface DeleteButtonProps {
  todoId: number;
  onDelete?: () => void;
  className?: string;
}

const DeleteButton = ({ todoId, onDelete, className = '' }: DeleteButtonProps) => {
  const [isDeleting, setIsDeleting] = useState(false);

  const handleDelete = async () => {
    if (!window.confirm('Are you sure you want to delete this todo?')) {
      return;
    }

    setIsDeleting(true);

    try {
      const response = await deleteTodo(todoId);

      if (response.error) {
        toast.error('Failed to delete todo');
        console.error('Delete error:', response.error);
        return;
      }

      toast.success('Todo deleted successfully!');

      if (onDelete) {
        onDelete();
      }
    } catch (err) {
      toast.error('An unexpected error occurred');
      console.error('Error deleting todo:', err);
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <button
      onClick={handleDelete}
      disabled={isDeleting}
      className={`px-3 py-1 bg-red-600 text-white text-sm rounded hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-1 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors ${className}`}
      aria-label="Delete todo"
    >
      {isDeleting ? 'Deleting...' : 'Delete'}
    </button>
  );
};

export default DeleteButton;