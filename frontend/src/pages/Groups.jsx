import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../api";

export default function Groups() {
  const [groups, setGroups] = useState([]);
  const [name, setName] = useState("");
  const [error, setError] = useState("");

  function loadGroups() {
    api.get("/groups/").then((res) => setGroups(res.data));
  }

  useEffect(() => {
    loadGroups();
  }, []);

  async function handleCreate(e) {
    e.preventDefault();
    setError("");
    try {
      await api.post("/groups/create", { name });
      setName("");
      loadGroups();
    } catch {
      setError("Couldn't create group.");
    }
  }

  return (
    <div className="page">
      <h1>Groups</h1>

      <form className="inline-form" onSubmit={handleCreate}>
        <input
          placeholder="Group name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
        />
        <button type="submit">Create group</button>
      </form>
      {error && <p className="form-error">{error}</p>}

      {groups.length === 0 && <p className="empty-note">No groups yet — create one above.</p>}

      <div className="group-list">
        {groups.map((g) => (
          <Link className="group-card" to={`/groups/${g.id}`} key={g.id}>
            <span className="group-card-name">{g.name}</span>
            <span className="group-card-arrow">›</span>
          </Link>
        ))}
      </div>
    </div>
  );
}