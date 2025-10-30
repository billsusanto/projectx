'use client';

import React, { useState } from 'react';
import toast from 'react-hot-toast';
import { updateTodo } from '@/lib/api';
import type { components } from '@/types/api';

type TodoRead = components['schemas']['TodoRead'];
type TodoUpdate = components['schemas']['TodoUpdate'];
type PriorityEnum = components['schemas']['PriorityEnum'];

interface TodoEditFormProps {
  todo: TodoRead;
  onSave: () => void;
  onCancel: () => void;
}

const TodoEditForm = ({ todo, onSave, onCancel }: TodoEditFormProps) => {
  const [title, setTitle] = useState(todo.title);
  const [description, setDescription] = useState(todo.description || '');
  const [completed, setCompleted] = useState(todo.completed);
  const [priority, setPriority] = useState<PriorityEnum | ''>(todo.priority || '');
  const [dueDate, setDueDate] = useState(
    todo.due_date ? new Date(todo.due_date).toISOString().split('T')[0] : ''
  );
  const [isSaving, setIsSaving] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!title.trim()) {
      toast.error('Title is required');
      return;
    }

    setIsSaving(true);

    try {
      const todoData: TodoUpdate = {
        title: title.trim(),
        description: description.trim() || null,
        completed,
        priority: priority || null,
        due_date: dueDate || null,
      };

      const response = await updateTodo(todo.id, todoData);

      if (response.error) {
        toast.error('Failed to update todo. Please try again.');
        return;
      }

      toast.success('Todo updated successfully!');
      onSave();
    } catch (err) {
      toast.error('An unexpected error occurred');
      console.error('Error updating todo:', err);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="p-4 border border-blue-200 rounded-lg">
      <div className="space-y-3">
        <div>
          <label htmlFor={`edit-title-${todo.id}`} className="block text-sm font-medium text-gray-700 mb-1">
            Title <span className="text-red-500">*</span>
          </label>
          <input
            id={`edit-title-${todo.id}`}
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            maxLength={200}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
            placeholder="Enter todo title"
            disabled={isSaving}
          />
        </div>

        <div>
          <label htmlFor={`edit-description-${todo.id}`} className="block text-sm font-medium text-gray-700 mb-1">
            Description
          </label>
          <textarea
            id={`edit-description-${todo.id}`}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={2}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
            placeholder="Enter todo description (optional)"
            disabled={isSaving}
          />
        </div>

        <div className="grid grid-cols-3 gap-3">
          <div>
            <label htmlFor={`edit-priority-${todo.id}`} className="block text-sm font-medium text-gray-700 mb-1">
              Priority
            </label>
            <select
              id={`edit-priority-${todo.id}`}
              value={priority}
              onChange={(e) => setPriority(e.target.value as PriorityEnum | '')}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
              disabled={isSaving}
            >
              <option value="">None</option>
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
            </select>
          </div>

          <div>
            <label htmlFor={`edit-dueDate-${todo.id}`} className="block text-sm font-medium text-gray-700 mb-1">
              Due Date
            </label>
            <input
              id={`edit-dueDate-${todo.id}`}
              type="date"
              value={dueDate}
              onChange={(e) => setDueDate(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
              disabled={isSaving}
            />
          </div>

          <div className="flex items-end">
            <label className="flex items-center space-x-2 cursor-pointer">
              <input
                type="checkbox"
                checked={completed}
                onChange={(e) => setCompleted(e.target.checked)}
                className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                disabled={isSaving}
              />
              <span className="text-sm font-medium text-gray-700">Completed</span>
            </label>
          </div>
        </div>

        <div className="flex gap-2 pt-2">
          <button
            type="submit"
            disabled={isSaving}
            className="flex-1 bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-1 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors text-sm"
          >
            {isSaving ? 'Saving...' : 'Save Changes'}
          </button>
          <button
            type="button"
            onClick={onCancel}
            disabled={isSaving}
            className="flex-1 bg-gray-200 text-gray-700 py-2 px-4 rounded-md hover:bg-gray-300 focus:outline-none focus:ring-2 focus:ring-gray-400 focus:ring-offset-1 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-sm"
          >
            Cancel
          </button>
        </div>
      </div>
    </form>
  );
};

export default TodoEditForm;
