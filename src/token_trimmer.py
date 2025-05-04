import os
import re
import argparse
import shutil
from pathlib import Path


class TokenTrimmer:
    """
    A tool to optimize code files by reducing unnecessary whitespace
    and formatting to minimize token usage while preserving functionality.
    """

    def __init__(self, input_dir, output_dir, file_extensions=None, preserve_md=False):
        """
        Initialize the code optimizer.
        
        Args:
            input_dir: Directory containing files to optimize
            output_dir: Directory where optimized files will be saved
            file_extensions: List of file extensions to process (None for all)
            preserve_md: Whether to preserve markdown files formatting
        """
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.file_extensions = file_extensions or ['.cs', '.py', '.js', '.ts', '.java', '.cpp', '.h', '.c', '.json', '.html', '.css']
        self.preserve_md = preserve_md
        self.stats = {
            'files_processed': 0,
            'blank_lines_removed': 0,
            'whitespace_chars_removed': 0,
            'bytes_saved': 0
        }
        
        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)

    def is_processable_file(self, file_path):
        """Check if the file should be processed based on its extension."""
        ext = file_path.suffix.lower()
        return ext in self.file_extensions or (ext == '.md' and not self.preserve_md)

    def optimize_file(self, file_path, output_path):
        """
        Optimize a single file by reducing whitespace while preserving functionality.
        
        Args:
            file_path: Path to the file to optimize
            output_path: Path where the optimized file will be saved
            
        Returns:
            Tuple of (blank lines removed, whitespace chars removed, bytes saved)
        """
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
                original_size = len(content)
                
            # Make sure output directory exists
            os.makedirs(output_path.parent, exist_ok=True)
            
            # Optimize content based on file type
            ext = file_path.suffix.lower()
            
            if ext in ['.py', '.cs', '.java', '.js', '.ts', '.cpp', '.c', '.h']:
                optimized_content = self._optimize_code(content, ext)
            elif ext in ['.json']:
                optimized_content = self._optimize_json(content)
            elif ext in ['.html', '.css']:
                optimized_content = self._optimize_markup(content)
            elif ext == '.md':
                optimized_content = self._optimize_markdown(content)
            else:
                # For unknown types, just do basic whitespace reduction
                optimized_content = self._optimize_generic(content)
            
            # Calculate metrics
            blank_lines_removed = content.count('\n\n') - optimized_content.count('\n\n')
            whitespace_chars_removed = content.count(' ') - optimized_content.count(' ')
            whitespace_chars_removed += content.count('\t') - optimized_content.count('\t')
            bytes_saved = original_size - len(optimized_content)
            
            # Write optimized content
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(optimized_content)
                
            return blank_lines_removed, whitespace_chars_removed, bytes_saved
            
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            # Copy the file as-is
            shutil.copy2(file_path, output_path)
            return 0, 0, 0

    def _optimize_code(self, content, ext):
        """Optimize code files while preserving syntax and functionality."""
        # Store code in strings/comments to protect them
        protected_parts = {}
        
        # Protect string literals
        if ext in ['.py', '.cs', '.java', '.js', '.ts']:
            # Protect triple-quoted strings in Python
            if ext == '.py':
                for i, match in enumerate(re.finditer(r'""".*?"""|\'\'\' .*?\'\'\'', content, re.DOTALL)):
                    key = f"__PROTECTED_STRING_{i}__"
                    protected_parts[key] = match.group(0)
                    content = content.replace(match.group(0), key)
            
            # Protect regular string literals
            for i, match in enumerate(re.finditer(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'', content)):
                key = f"__PROTECTED_STRING_{i + 100}__"  # Offset to avoid conflicts
                protected_parts[key] = match.group(0)
                content = content.replace(match.group(0), key)
        
        # Protect comments
        if ext == '.py':
            # Protect Python comments
            for i, match in enumerate(re.finditer(r'#.*?$', content, re.MULTILINE)):
                key = f"__PROTECTED_COMMENT_{i}__"
                protected_parts[key] = match.group(0)
                content = content.replace(match.group(0), key)
        elif ext in ['.cs', '.java', '.cpp', '.c', '.h', '.js', '.ts']:
            # Protect C-style comments (both // and /* */)
            for i, match in enumerate(re.finditer(r'//.*?$|/\*.*?\*/', content, re.MULTILINE | re.DOTALL)):
                key = f"__PROTECTED_COMMENT_{i}__"
                protected_parts[key] = match.group(0)
                content = content.replace(match.group(0), key)
        
        # Reduce multiple blank lines to at most one
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        # Reduce excessive indentation without changing code structure
        lines = content.splitlines()
        
        # Process line by line
        for i in range(len(lines)):
            # Remove trailing whitespace
            lines[i] = lines[i].rstrip()
            
            # Normalize indentation (keep tabs or spaces, just make them consistent)
            if lines[i].startswith(' '):
                # Count leading spaces
                leading_spaces = len(lines[i]) - len(lines[i].lstrip(' '))
                # Normalize to consistent indentation
                if leading_spaces > 0 and leading_spaces % 4 == 0:
                    # For 4-space indentation, normalize to exact multiples
                    indent_level = leading_spaces // 4
                    lines[i] = ' ' * (indent_level * 4) + lines[i].lstrip(' ')
        
        # Rejoin the lines
        content = '\n'.join(lines)
        
        # Restore protected parts
        for key, value in protected_parts.items():
            content = content.replace(key, value)
        
        return content

    def _optimize_json(self, content):
        """Optimize JSON files by removing unnecessary whitespace."""
        try:
            import json
            # Parse and compact JSON
            parsed = json.loads(content)
            return json.dumps(parsed, separators=(',', ':'))
        except:
            # If JSON parsing fails, do basic whitespace reduction
            return self._optimize_generic(content)

    def _optimize_markup(self, content):
        """Optimize HTML/CSS files while preserving structure."""
        # Remove comments
        content = re.sub(r'<!--.*?-->', '', content, flags=re.DOTALL)
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
        
        # Collapse multiple spaces to single space
        content = re.sub(r' {2,}', ' ', content)
        
        # Remove spaces around tags
        content = re.sub(r'>\s+<', '><', content)
        
        # Reduce multiple blank lines
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        return content

    def _optimize_markdown(self, content):
        """
        Optimize markdown while preserving rendering.
        More careful with whitespace as it affects rendering.
        """
        # Protect code blocks
        protected_parts = {}
        for i, match in enumerate(re.finditer(r'```.*?```', content, re.DOTALL)):
            key = f"__PROTECTED_CODE_{i}__"
            protected_parts[key] = match.group(0)
            content = content.replace(match.group(0), key)
        
        # Reduce multiple blank lines to at most two (markdown often needs two for paragraph breaks)
        content = re.sub(r'\n{4,}', '\n\n\n', content)
        
        # Remove trailing whitespace from lines
        lines = content.splitlines()
        for i in range(len(lines)):
            # Keep trailing spaces for line breaks in markdown
            if not lines[i].endswith('  '):
                lines[i] = lines[i].rstrip()
        
        content = '\n'.join(lines)
        
        # Restore protected parts
        for key, value in protected_parts.items():
            content = content.replace(key, value)
        
        return content

    def _optimize_generic(self, content):
        """Generic optimization for unknown file types."""
        # Reduce multiple blank lines to at most one
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        # Remove trailing whitespace
        lines = content.splitlines()
        for i in range(len(lines)):
            lines[i] = lines[i].rstrip()
            
        content = '\n'.join(lines)
        return content

    def process_directory(self):
        """Process all relevant files in the input directory."""
        # Copy directory structure first
        for root, dirs, files in os.walk(self.input_dir):
            for dir_name in dirs:
                src_path = Path(root) / dir_name
                rel_path = src_path.relative_to(self.input_dir)
                dst_path = self.output_dir / rel_path
                os.makedirs(dst_path, exist_ok=True)
        
        # Process files
        for root, dirs, files in os.walk(self.input_dir):
            for file_name in files:
                src_path = Path(root) / file_name
                rel_path = src_path.relative_to(self.input_dir)
                dst_path = self.output_dir / rel_path
                
                if self.is_processable_file(src_path):
                    blank_removed, whitespace_removed, bytes_saved = self.optimize_file(src_path, dst_path)
                    
                    self.stats['files_processed'] += 1
                    self.stats['blank_lines_removed'] += blank_removed
                    self.stats['whitespace_chars_removed'] += whitespace_removed
                    self.stats['bytes_saved'] += bytes_saved
                    
                    print(f"Optimized: {rel_path} (saved {bytes_saved} bytes)")
                else:
                    # Copy non-processable files as-is
                    os.makedirs(dst_path.parent, exist_ok=True)
                    shutil.copy2(src_path, dst_path)
                    print(f"Copied: {rel_path}")
        
        return self.stats


def main():
    parser = argparse.ArgumentParser(
        description="Optimize code files to reduce whitespace while preserving functionality."
    )
    parser.add_argument("input_dir", help="Directory containing files to optimize")
    parser.add_argument("output_dir", help="Directory where optimized files will be saved")
    parser.add_argument(
        "--extensions", 
        help="Comma-separated list of file extensions to process (e.g., .cs,.py,.js)", 
        default=".cs,.py,.js,.ts,.java,.cpp,.h,.c,.json,.html,.css"
    )
    parser.add_argument(
        "--preserve-md",
        action="store_true",
        help="Preserve markdown formatting (don't optimize .md files)"
    )
    
    args = parser.parse_args()
    
    # Parse file extensions
    extensions = [ext.strip() if ext.strip().startswith('.') else f'.{ext.strip()}' 
                 for ext in args.extensions.split(',')]
    
    # Initialize and run optimizer
    optimizer = TokenTrimmer(
        args.input_dir, 
        args.output_dir, 
        file_extensions=extensions,
        preserve_md=args.preserve_md
    )
    
    stats = optimizer.process_directory()
    
    # Print summary
    print("\nOptimization Summary:")
    print(f"Files processed: {stats['files_processed']}")
    print(f"Blank lines removed: {stats['blank_lines_removed']}")
    print(f"Whitespace characters removed: {stats['whitespace_chars_removed']}")
    print(f"Total bytes saved: {stats['bytes_saved']} ({stats['bytes_saved'] / 1024:.2f} KB)")


if __name__ == "__main__":
    main()