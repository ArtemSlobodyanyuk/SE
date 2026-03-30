const API = "http://localhost:5000";

async function loadTasks() {
  const res = await fetch(`${API}/tasks`);
  const tasks = await res.json();

  const list = document.getElementById("tasks");
  list.innerHTML = "";

  tasks.forEach(t => {
    const li = document.createElement("li");
    li.innerHTML = `
      <b>${t.title}</b><br>
      ${t.description || ""}
      <button onclick="deleteTask(${t.id})">❌</button>
    `;
    list.appendChild(li);
  });
}

async function createTask() {
  const title = document.getElementById("title").value;
  const desc = document.getElementById("desc").value;

  await fetch(`${API}/tasks`, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({ title, description: desc })
  });

  loadTasks();
}

async function deleteTask(id) {
  await fetch(`${API}/tasks/${id}`, { method: "DELETE" });
  loadTasks();
}

loadTasks();