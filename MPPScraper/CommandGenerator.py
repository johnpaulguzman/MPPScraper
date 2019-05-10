class CommandGenerator:
    def __init__(self, template, replace_dict):
        self.template = template
        self.replace_dict = replace_dict

    def generate_commands(self):
        commands = [self.template]
        for keyword, replacements in self.replace_dict.items():
            commands = [command.replace(str(keyword), str(replacement)) for command in commands for replacement in replacements]
        return commands

    def split_commands(self, splits):
        commands = self.generate_commands()
        division = len(commands) / splits
        return [commands[round(division * i):round(division * (i + 1))] for i in range(splits)]


if __name__ == '__main__':
    test_template = "echo <OPT1> <OPT2>"
    test_replace_dict = {
        "<OPT1>": ["1", "2", 3],
        "<OPT2>": [True, False], }
    commandGenerator = CommandGenerator(test_template, test_replace_dict)
    print(commandGenerator.generate_commands())
    print(commandGenerator.split_commands(2))
