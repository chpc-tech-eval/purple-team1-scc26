// PostgreSQL access. Connection settings come only from the environment that
// Kubernetes injects from the postgres-credentials SealedSecret.
import pg from "pg";

export const pool = new pg.Pool({
  host: process.env.POSTGRES_HOST || "postgres",
  port: Number(process.env.POSTGRES_PORT || 5432),
  user: process.env.POSTGRES_USER,
  password: process.env.POSTGRES_PASSWORD,
  database: process.env.POSTGRES_DB,
  max: 5,
});

// Idempotent schema: the Week-3 contract (platform/README.md) plus sessions.
export async function migrate() {
  await pool.query(`
    CREATE TABLE IF NOT EXISTS teams (
      id SERIAL PRIMARY KEY,
      name TEXT NOT NULL,
      project_slug TEXT NOT NULL UNIQUE
    );
    CREATE TABLE IF NOT EXISTS users (
      id SERIAL PRIMARY KEY,
      username TEXT NOT NULL UNIQUE,
      display_name TEXT NOT NULL,
      password_hash TEXT NOT NULL,
      team_id INTEGER REFERENCES teams(id),
      created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    );
    CREATE TABLE IF NOT EXISTS sessions (
      token_hash TEXT PRIMARY KEY,
      user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      expires_at TIMESTAMPTZ NOT NULL
    );
    CREATE TABLE IF NOT EXISTS logins (
      id BIGSERIAL PRIMARY KEY,
      user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
      at TIMESTAMPTZ NOT NULL DEFAULT now()
    );
  `);
}

// Seed the team and its members once. PLATFORM_SEED_USERS comes from a
// SealedSecret: "username:Display Name:password;..." (passwords are hashed
// here; an existing user is never overwritten).
export async function seed(bcrypt) {
  const { rows } = await pool.query(
    `INSERT INTO teams (name, project_slug) VALUES ($1, $2)
     ON CONFLICT (project_slug) DO UPDATE SET name = EXCLUDED.name RETURNING id`,
    [process.env.PLATFORM_TEAM_NAME || "3NCRYP+3D", process.env.PLATFORM_PROJECT_SLUG || "purple-team1-scc26"],
  );
  const teamId = rows[0].id;
  const spec = process.env.PLATFORM_SEED_USERS || "";
  for (const entry of spec.split(";").map((s) => s.trim()).filter(Boolean)) {
    const [username, displayName, password] = entry.split(":");
    if (!username || !displayName || !password) continue;
    const exists = await pool.query("SELECT 1 FROM users WHERE username = $1", [username]);
    if (exists.rowCount) continue;
    const hash = await bcrypt.hash(password, 12);
    await pool.query(
      "INSERT INTO users (username, display_name, password_hash, team_id) VALUES ($1, $2, $3, $4)",
      [username, displayName, hash, teamId],
    );
  }
}
