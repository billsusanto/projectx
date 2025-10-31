'use client';

import React, { useState } from 'react';
import TodoList from '@/components/todos/TodoList';
import TodoForm from '@/components/todos/TodoForm';

const Home = () => {
  const [refreshKey, setRefreshKey] = useState(0);

  const handleTodoCreated = () => {
    setRefreshKey((prev) => prev + 1);
  };

  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold mb-8 text-gray-800">Todo App</h1>

      <div className="mb-8">
        <TodoForm onTodoCreated={handleTodoCreated} />
      </div>

      <TodoList key={refreshKey} />
    </div>
  );
};

export default Home;