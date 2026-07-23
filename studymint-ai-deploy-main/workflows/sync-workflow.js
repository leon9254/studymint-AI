const fs = require("fs");
const path = require("path");

const sqlite3 = require("/usr/local/lib/node_modules/n8n/node_modules/sqlite3");

const dbPath = process.env.DB_SQLITE_DATABASE || "/home/node/.n8n/database.sqlite";
const inputPath = process.argv[2];

if (!inputPath) {
  console.error("Usage: node sync-workflow.js <workflow.json>");
  process.exit(2);
}

const workflow = JSON.parse(fs.readFileSync(inputPath, "utf8"));
const db = new sqlite3.Database(dbPath);

function asJson(value, fallback) {
  return JSON.stringify(value === undefined ? fallback : value);
}

function all(sql, params = []) {
  return new Promise((resolve, reject) => {
    db.all(sql, params, (error, rows) => (error ? reject(error) : resolve(rows)));
  });
}

function get(sql, params = []) {
  return new Promise((resolve, reject) => {
    db.get(sql, params, (error, row) => (error ? reject(error) : resolve(row)));
  });
}

function run(sql, params = []) {
  return new Promise((resolve, reject) => {
    db.run(sql, params, function onRun(error) {
      if (error) {
        reject(error);
        return;
      }
      resolve(this);
    });
  });
}

async function main() {
  const row = await get("SELECT id FROM workflow_entity WHERE name = ?", [workflow.name]);
  if (!row) {
    console.log(`Workflow not found: ${workflow.name}`);
    process.exitCode = 3;
    return;
  }

  const columns = new Set((await all("PRAGMA table_info(workflow_entity)")).map((column) => column.name));
  const updates = {
    name: workflow.name,
    active: workflow.active ? 1 : 0,
    nodes: asJson(workflow.nodes, []),
    connections: asJson(workflow.connections, {}),
    settings: asJson(workflow.settings, {}),
    staticData: asJson(workflow.staticData, null),
    pinData: asJson(workflow.pinData, {}),
    versionId: workflow.versionId || null,
    updatedAt: new Date().toISOString(),
  };

  const assignments = [];
  const values = [];
  for (const [column, value] of Object.entries(updates)) {
    if (!columns.has(column)) {
      continue;
    }
    assignments.push(`${column} = ?`);
    values.push(value);
  }

  if (!assignments.length) {
    throw new Error("No compatible workflow_entity columns were found");
  }

  values.push(row.id);
  await run(`UPDATE workflow_entity SET ${assignments.join(", ")} WHERE id = ?`, values);
  console.log(`Synced workflow ${workflow.name} (${row.id}) from ${path.basename(inputPath)}`);
}

main()
  .catch((error) => {
    console.error(error);
    process.exitCode = 1;
  })
  .finally(() => db.close());
