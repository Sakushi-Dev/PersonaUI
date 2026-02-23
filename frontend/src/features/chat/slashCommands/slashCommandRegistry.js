// ── Slash Command Registry ──
// Central registry for all slash commands.
// To add a new command, simply push to the `commands` array or use `register()`.

const commands = [];

/**
 * Register a new slash command.
 * @param {object} cmd
 * @param {string} cmd.name        – The command keyword (without leading "/")
 * @param {string} cmd.description – Short description shown in the menu
 * @param {function} cmd.execute   – Called when command is confirmed. Receives { args: string }
 */
export function register(cmd) {
  if (!cmd.name || !cmd.execute) {
    console.warn('[SlashCommands] register: name and execute are required', cmd);
    return;
  }
  // Avoid duplicates
  if (commands.find((c) => c.name === cmd.name)) {
    console.warn(`[SlashCommands] command "/${cmd.name}" already registered`);
    return;
  }
  commands.push(cmd);
}

/**
 * Return all registered commands, optionally filtered by a query string.
 * @param {string} [query] – Filter text (without leading "/")
 * @returns {Array<{name: string, description: string, execute: function}>}
 */
export function getCommands(query = '') {
  const q = query.toLowerCase();
  return commands.filter(
    (c) =>
      c.name.toLowerCase().startsWith(q) ||
      c.description.toLowerCase().includes(q)
  );
}

/**
 * Find exactly one command by name.
 */
export function findCommand(name) {
  return commands.find((c) => c.name.toLowerCase() === name.toLowerCase());
}

export default { register, getCommands, findCommand };
