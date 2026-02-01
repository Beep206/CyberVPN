import 'package:flutter/material.dart';

class CyberAppBar extends StatelessWidget implements PreferredSizeWidget {
  final String? title;
  final Widget? titleWidget;
  final List<Widget>? actions;
  final Widget? leading;
  final bool centerTitle;
  final bool transparent;

  const CyberAppBar({
    super.key,
    this.title,
    this.titleWidget,
    this.actions,
    this.leading,
    this.centerTitle = true,
    this.transparent = false,
  });

  @override
  Size get preferredSize => const Size.fromHeight(kToolbarHeight);

  @override
  Widget build(BuildContext context) {
    return AppBar(
      title: titleWidget ?? (title != null ? Text(title!) : null),
      actions: actions,
      leading: leading,
      centerTitle: centerTitle,
      backgroundColor: transparent ? Colors.transparent : null,
      elevation: transparent ? 0 : null,
    );
  }
}
