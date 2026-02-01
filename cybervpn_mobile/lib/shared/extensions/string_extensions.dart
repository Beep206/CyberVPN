extension StringExtensions on String {
  String get capitalize =>
      isEmpty ? this : '${this[0].toUpperCase()}${substring(1)}';

  String get capitalizeWords =>
      split(' ').map((w) => w.capitalize).join(' ');

  bool get isValidEmail =>
      RegExp(r'^[\w-\.]+@([\w-]+\.)+[\w-]{2,4}$').hasMatch(this);

  String get masked => length <= 4
      ? this
      : '${substring(0, 2)}${'*' * (length - 4)}${substring(length - 2)}';

  String truncate(int maxLength, {String suffix = '...'}) =>
      length <= maxLength
          ? this
          : '${substring(0, maxLength - suffix.length)}$suffix';
}
