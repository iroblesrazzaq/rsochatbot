import fs from 'fs/promises';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PORT_FILE = path.join(__dirname, 'port.txt');

export const savePort = async (port) => {
  try {
    await fs.writeFile(PORT_FILE, port.toString());
    console.log(`Port ${port} saved to ${PORT_FILE}`);
  } catch (error) {
    console.error('Error saving port:', error);
  }
};