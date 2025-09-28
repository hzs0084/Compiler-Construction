import re

def remove_comments(source_code):
        # Remove multi-line comments /* ... */
        multiline_comment = re.compile(r'/\*.*?\*/', re.DOTALL)
        source_code = multiline_comment.sub('', source_code)
        
        # Remove single-line comments // ...
        oneline_comment = re.compile(r'//.*')
        source_code = oneline_comment.sub('', source_code)

        return source_code


# def main(source_code):
    