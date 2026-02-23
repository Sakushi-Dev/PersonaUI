// ── Barrel export for slash commands ──
export { register, getCommands, findCommand } from './slashCommandRegistry';
import './builtinCommands'; // self-registering side-effect
