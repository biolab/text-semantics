import logging
import os


EXCLUDED = ["index.html", "README.md", ".nojekyll"]


file_path = os.path.dirname(os.path.realpath(__file__))
with open(os.path.join(file_path, "index.html")) as f:
    template_index = f.read()
template_a = "<a href='{link}/'>{name}</a>"


def generate(dir):
    logging.info(f"Processing dir {dir}")
    filenames, dirnames = [], []
    for f_name in sorted(os.listdir(dir)):
        if f_name not in EXCLUDED and not f_name.startswith(("_", ".")):
            if os.path.isfile(os.path.join(dir, f_name)):
                filenames.append(f_name)
            else:
                dirnames.append(f_name)

    a_ = [template_a.format(link=file, name=file) for file in dirnames + filenames]
    index_ = template_index.format(files="\n".join(a_), path=dir.replace(".", ""))
    with open(os.path.join(dir, "index.html"), "w") as f:
        f.write(index_)

    for subdir in dirnames:
        generate(os.path.join(dir, subdir))


if __name__ == "__main__":
    generate(".")
