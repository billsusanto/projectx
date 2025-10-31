"use client";

import React, { useEffect, useState } from 'react';
import toast from 'react-hot-toast';
import { apiClient } from '@/lib/api';
import DeleteButton from '@/components/ui/DeleteButton';
import EditButton from '@/components/ui/EditButton';
import TodoEditForm from '@/components/todos/TodoEditForm';
import type { components } from '@/types/types';

type Todo = components['schemas']['TodoRead'];

const TodoList = () => {
  const [todos, setTodos] = useState<Todo[]>([]);
  const [loading, setLoading] = useState(true);
  const [editingId, setEditingId] = useState<number | null>(null);

  const fetchTodos = async (showLoading = false) => {
    if (showLoading) {
      setLoading(true);
    }

    const { data, error } = await apiClient.GET('/todos/');

    if (error) {
      toast.error('Failed to fetch todos');
    } else {
      setTodos(data || []);
    }

    if (showLoading) {
      setLoading(false);
    }
  };

  useEffect(() => {
    const loadInitialTodos = async () => {
      const { data, error } = await apiClient.GET('/todos/');

      if (error) {
        toast.error('Failed to fetch todos');
      } else {
        setTodos(data || []);
      }

      setLoading(false);
    };

    loadInitialTodos();
  }, []);

  const handleTodoDeleted = () => {
    fetchTodos(false);
  };

  const handleEdit = (todoId: number) => {
    setEditingId(todoId);
  };

  const handleCancelEdit = () => {
    setEditingId(null);
  };

  const handleSaveEdit = () => {
    setEditingId(null);
    fetchTodos(false);
  };

  if (loading) return <div className="text-center py-4">Loading...</div>;
  if (todos.length === 0) return <div className="text-gray-500 text-center py-4">No todos yet. Create one above!</div>;

  return (
    <div>
      <h2 className="text-2xl font-semibold mb-4 text-gray-800">Your Todos</h2>
      <div className="space-y-3">
        {todos.map((todo) => (
          <div key={todo.id}>
            {editingId === todo.id ? (
              <TodoEditForm
                todo={todo}
                onSave={handleSaveEdit}
                onCancel={handleCancelEdit}
              />
            ) : (
              <div className="p-4 bg-white border border-gray-200 rounded-lg shadow-sm hover:shadow-md transition-shadow">
                <div className="flex justify-between items-start">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <h3 className="text-lg font-semibold text-gray-800">{todo.title}</h3>
                      {todo.priority && (
                        <span className={`px-2 py-0.5 text-xs rounded-full ${
                          todo.priority === 'high' ? 'bg-red-100 text-red-700' :
                          todo.priority === 'medium' ? 'bg-yellow-100 text-yellow-700' :
                          'bg-green-100 text-green-700'
                        }`}>
                          {todo.priority}
                        </span>
                      )}
                    </div>
                    {todo.description && (
                      <p className="text-gray-600 mb-2">{todo.description}</p>
                    )}
                    <div className="flex items-center gap-4 text-sm text-gray-500">
                      <span>
                        Status: <span className={todo.completed ? 'text-green-600 font-medium' : 'text-gray-600'}>
                          {todo.completed ? 'Completed' : 'Pending'}
                        </span>
                      </span>
                      {todo.due_date && (
                        <span>Due: {new Date(todo.due_date).toLocaleDateString()}</span>
                      )}
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <EditButton onEdit={() => handleEdit(todo.id)} />
                    <DeleteButton todoId={todo.id} onDelete={handleTodoDeleted} />
                  </div>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

export default TodoList;