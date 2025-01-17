# Documentation Guide for `createdNoteOn` Function

## Original Function
```dart
bool createdNoteOn(String dictName, NoteVO parentNote,
      {required String label, String? subLangLabel, required String description, String? subLangDescription})
```

## Recommended Documentation Style

```dart
/// Creates a new note entry in the specified dictionary under a parent note.
///
/// Takes a [dictName] to specify the target dictionary and a [parentNote] under which
/// the new note will be created. The note requires a [label] in the primary language
/// and a [description] of the note's characteristics.
///
/// Parameters:
/// * [dictName] - The name of the dictionary where the note will be created
/// * [parentNote] - The parent note under which this new note will be nested
/// * [label] - The primary language label for the note
/// * [subLangLabel] - Optional secondary language label (defaults to null)
/// * [description] - The primary language description of the note
/// * [subLangDescription] - Optional secondary language description (defaults to null)
///
/// Returns:
/// * `true` if the note was successfully created
/// * `false` if creation failed (e.g., dictionary not found or duplicate note)
///
/// Example:
/// ```dart
/// final parentNote = getNoteByLabel('Fruity');
/// final success = createdNoteOn(
///   'Coffee Flavors',
///   parentNote,
///   label: 'Berry',
///   description: 'Reminiscent of fresh berries',
/// );
/// ```
///
/// Throws:
/// * [Exception] if the dictionary name is invalid or parent note doesn't exist
```

## Documentation Style Breakdown

### 1. Overview Line
```dart
/// Creates a new note entry in the specified dictionary under a parent note.
```
- Starts with a verb
- One concise sentence
- No period at the end
- Immediately clear purpose

### 2. Detailed Description
```dart
/// Takes a [dictName] to specify the target dictionary and a [parentNote] under which
/// the new note will be created. The note requires a [label] in the primary language
/// and a [description] of the note's characteristics.
```
- Uses parameter references in brackets
- Explains relationships between parameters
- Provides context
- Maintains line length limit

### 3. Parameters Section
```dart
/// Parameters:
/// * [dictName] - The name of the dictionary where the note will be created
/// * [parentNote] - The parent note under which this new note will be nested
/// * [label] - The primary language label for the note
/// * [subLangLabel] - Optional secondary language label (defaults to null)
/// * [description] - The primary language description of the note
/// * [subLangDescription] - Optional secondary language description (defaults to null)
```
- Bullet points for clarity
- Consistent formatting
- Indicates optional parameters
- Clear descriptions

### 4. Return Value
```dart
/// Returns:
/// * `true` if the note was successfully created
/// * `false` if creation failed (e.g., dictionary not found or duplicate note)
```
- Uses backticks for values
- Explains both outcomes
- Provides failure examples

### 5. Example Usage
```dart
/// Example:
/// ```dart
/// final parentNote = getNoteByLabel('Fruity');
/// final success = createdNoteOn(
///   'Coffee Flavors',
///   parentNote,
///   label: 'Berry',
///   description: 'Reminiscent of fresh berries',
/// );
/// ```
```
- Shows complete, working example
- Uses realistic values
- Proper formatting and indentation

### 6. Exceptions
```dart
/// Throws:
/// * [Exception] if the dictionary name is invalid or parent note doesn't exist
```
- Lists exception types
- Explains trigger conditions
- Helps with error handling