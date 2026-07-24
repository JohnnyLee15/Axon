import subprocess

from .tool_contracts import TOOL_RESULTS


def _format_shell_result(result: subprocess.CompletedProcess[str]) -> str:
    output_parts = []

    stdout = result.stdout.strip()
    stderr = result.stderr.strip()

    if stdout:
        output_parts.append(stdout)

    if stderr:
        output_parts.append(f"STDERR:\n{stderr}")

    if not output_parts:
        if result.returncode == 0:
            return "# Command executed successfully (no output)."

        return f"# Command failed with exit code {result.returncode} (no output)."

    content = "\n".join(output_parts)
    if result.returncode != 0:
        content = f"Exit code: {result.returncode}\n{content}"

    return content


def execute_shell_cmd(cmd: str) -> dict[str, str]:
    cmd = cmd.strip()

    if not cmd:
        return {TOOL_RESULTS.CONTENT: "# No command provided."}

    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
        )
        content = _format_shell_result(result)
    except Exception as e:
        content = f"# Shell execution error: {e}"

    return {TOOL_RESULTS.CONTENT: content}
