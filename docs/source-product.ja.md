# ���{��W����Android 10 GSI�\�[�X�ݒ�

**�\�[�X���������������i�K�ł��Bsystem.img�̃R���p�C���A���@�N���A�������݂͖����؂ł��B**
`download-base.cmd` ���擾�������GSI�ɂ́A���̍����͓K�p����܂���B

## �������e

| ���� | �\�[�X�ݒ� | ���m�F���� |
| --- | --- | --- |
| �������� | `PRODUCT_LOCALES := ja_JP en_US`�B�����l�͓��{��A�p����I�����Ɏc�� | ���@�̏����ݒ��ʁB����userdata�̌���͋����ύX���Ȃ� |
| �r���h�Ώ� | `suiram_ctz10-userdebug`�APHH arm64/SAR vanilla/N�h�� | �SAndroid�c���[�ł̃R���p�C���E�N�� |
| �{�[�h | `phhgsi_arm64_ab` ��ێ� | CTZ�̕����X���b�g�\�����Ӗ����Ȃ� |
| ADB | PHH�� `base.mk` �� `system.prop` �̗����� `ro.adb.secure=0` �� `1` �ɕύX | stock vendor���̃v���p�e�B���܂ގ��@�̍ŏI���� |
| USB�����\�� | PHH�� `persist.sys.usb.config=adb` �� `mtp` �ɕύX | ���@�ł�MTP���� |
| �O�����o�[�X�f�o�b�O | PHH��dbclient�E���o�[�X�f�o�b�O�pscript�Einit�ݒ�̃R�s�[�����O | �W��ADB�̎��@����BOS�S�̂̈��S����ۏ؂�����̂ł͂Ȃ� |
| �ǉ��A�v�� | `phh-su`�E`me.phh.superuser`�EGApps��ǉ����Ȃ� | userdebug���̂͊J���p�B���S���E�F�؂͕ۏ؂��Ȃ� |

���{��UI�Ɠ��{��L�[�{�[�h�͕ʂł��BAndroid 10�c���[�Ŋm�F�ł��Ă��Ȃ�IME���W���[����
�����Œǉ������A���{����͂̑g�ݍ��݂Ɠ���m�F�͎c��ƂƂ��܂��B
[nicoWnnG�̕�APK�r���h](japanese-ime.ja.md)���������܂������A���i�� `PRODUCT_PACKAGES` �ւ͂܂��ǉ����Ă��܂���B
timezone�A��ʉ�]�A�^�b�`�AHAL�Akernel�ASELinux�ݒ�͂��̍����ŕύX���܂���B

## �㗬�̌Œ�͈�

[source-profile.json](../config/source-profile.json) ��AOSP�^�O�APHH�e�R���|�[�l���g��commit��
����11�t�@�C����Git blob SHA���L�^���Ă��܂��Bv222���J�����ɑΉ����闚������I��
�R���|�[�l���g�̃X�i�b�v�V���b�g�ł���A**v222�z�z�o�C�i���Ɗ��S��v����manifest�ł͂���܂���**�B
SHA1�͓��͕ύX�̌��o�p�ŁA������z�z���̐^�����̏ؖ��ł͂���܂���B
�c��̈ˑ����܂�[����manifest��commit�L�^�c�[��](source-build.ja.md)���������܂����B
���ۂ̑S�����Ecommit�L�^�E���C�Z���X�m�F�EAndroid�r���h�͂܂��K�v�ł��B

�m�F�����㗬�F

- [v222 build.sh](https://github.com/phhusson/treble_experimentations/blob/4a5cabb317a69ccf646c5742f88d3345a9ccbecf/build.sh)
- [PHH�̐��i�������V�s](https://github.com/phhusson/device_phh_treble/blob/64289357288a82fc9771c013b54f9e0833689599/generate.sh)
- [PHH��Android build](https://github.com/phhusson/platform_build/tree/165f02822b54b3651fb388fc425ea9f3b416b496)
- [PHH VNDK](https://github.com/phhusson/vendor_vndk/tree/cea8e7093616005e68fd527a2acd81f9f2af30c3)
- [PHH manifest�̗���](https://github.com/phhusson/treble_manifest/tree/b66f014948ac17c700fc4eb746c3b56b381611c2)
- [PHH system.prop](https://github.com/phhusson/device_phh_treble/blob/64289357288a82fc9771c013b54f9e0833689599/system.prop)
- [Android 10�̋N�����v���p�e�B�ǂݍ���](https://github.com/phhusson/platform_system_core/blob/67841c06d5c532acfd83cab9b38ab9c909ef5a2a/init/property_service.cpp)

`board-base.mk` ��PHH�� `system.prop` �� `TARGET_SYSTEM_PROP` �ɒǉ����܂��B
Android build�͂����system�� `build.prop` �֊܂߂܂��BAndroid 10��init�ł͌ォ��ǂ�
`build.prop` �̒l�� `prop.default` �̒l���㏑���ł��邽�߁A`base.mk` �����̏C���ł�
ADB�F�؂���т��ėL���ɂł��܂���B2�t�@�C���𓯂��l�֏C�����A������̌����ł�
system���̎����l���m�F���܂��Bstock vendor�̒l�͂��̃\�[�X�����ł͊m�F�ł��܂���B

�㗬 `build.sh` ��reset/clean/force-sync���������s���܂���B
���̓K�p�R�}���h�̓\�[�X�����A�_�E�����[�h�AAndroid�r���h�A�[����������s���܂���B
�S�����E�r���h�͕ʂ̍H�������i�[��GitHub Actions�ōs���܂��B

## ��p�\�[�X�f�B���N�g���ւ̓K�p

Linux��Python 3.9�ȏ��z�肵�܂��B�܂��ʃf�B���N�g���ɏ㗬Android 10�\�[�X���������A
�S�ˑ����܂�manifest�̐��������m�F����K�v������܂��B[�����\�[�X�菇](source-build.ja.md)��
�����ς݂ł����A�����E�r���h�����͖��m�F�ł��B�ȉ��� `/path/to/...` �͎��ۂ̏ꏊ�֒u�������Ă��������B

```sh
# �f�t�H���g�͌����̂݁B�[���ɂ͉������Ȃ��B
python3 /path/to/ctz-rom/scripts/prepare-gsi-source.py /path/to/android

# ������ʂ������͂Ɍ���A�����I�Ƀ\�[�X������K�p����B
python3 /path/to/ctz-rom/scripts/prepare-gsi-source.py /path/to/android --apply
```

�c�[���͑S���͂��������Ă���A���i�ݒ�Ɠo�^��ǉ����APHH���� `base.mk` ��2���ڂ�
`system.prop` ��ADB�F�ؐݒ��ύX���APHH�̊O�����o�[�X�f�o�b�O�p3�t�@�C���̃R�s�[�����O���܂��B
**�����̋��ʃt�@�C���̕ύX�͓����c���[�̑���PHH���i�ɂ��e�����܂��B������ƃc���[�Ƌ��L���Ȃ��ł��������B**
����base.mk�Esystem.prop�EAndroidProducts.mk�Eoverlay.mk�� `.ctz-original` �Ƃ��ĕۑ����܂��B
������̓��e�����́A����3�t�@�C�������݂��Ȃ����Ƃ��m�F���A����symlink�����ۂ��܂��B
���m�̓��́E�ύX�ςݏo�́E�����o�b�N�A�b�v�Esymlink�����ۂ��A������ԂōĎ��s����ƕύX���܂���B
I/O��Q���̑S�t�@�C���ꊇ���[���o�b�N�͂���܂���B�r���Ŏ��s�����ꍇ�͍����ƃo�b�N�A�b�v��
�蓮�m�F���A�����ēK�p��o�b�N�A�b�v�폜�ŉ����؂�Ȃ��ł��������B

���S�ȃ\�[�X�����������**�����؂̃r���h�Ώ�**�͎��̂Ƃ���ł��B

```sh
cd /path/to/android
source build/envsetup.sh
lunch suiram_ctz10-userdebug
m -j4 systemimage
```

����͐����m�F�ς݂̃r���h�菇�ł͂���܂���B�R���p�C�������̏؋������ʕ����܂�����܂���B
���̌o�H�ł� `generate.sh` �����s���܂���B�K�v�Ȑ��i�o�^�͓K�p�c�[�����ǉ����܂��B

## CTZ�Ŏg��Ȃ�Qualcomm�⏕�A�v��

2026-10-05��[�L���b�V�����p�r���h](https://github.com/godrenkon/Challenge_Pad-Android10-ROM/actions/runs/37318904117)��
Ninja 97%�� `QtiAudio` ��Java�R���p�C���Ɏ��s���܂����B�Œ肳�ꂽ�㗬�̐����R�[�h��
Android 10�̃N���X�p�X�ɂȂ� `android.hidl.base.V1_0` �� `IHwBinder.FLAG_ONEWAY` ���Q�Ƃ��Ă��܂��B
���̃A�v����Qualcomm�̖����E�ʘb����HAL��OnePlus6�̃X�C�b�`�p�ŁAMT8168��CTZ�ɂ͎g�p���܂���B
�m�F����[�㗬Service.java](https://github.com/phhusson/vendor_hardware_overlay/blob/7293fa02e43ce63f07b95dc44d7ab6aec262407e/Qualcomm/QtiAudio/src/me/phh/qti/audio/Service.java)�Ɋ�Â��A
`vendor/hardware_overlay/overlay.mk` �̐��i�p�b�P�[�W�ꗗ���炱�̃A�v�������������܂��B
���t�@�C����Git blob SHA�ƌ��̃u���b�N���������A���{��ۑ����܂��B
MediaTek������overlay�⋤�ʂ�Treble�⏕�A�v���͈��������܂߂܂��B
���̕ύX����p�\�[�X�c���[�̑���PHH���i�ɉe�����邽�߁A���̃c���[�𑼒[���̃r���h�Ƌ��L���Ȃ��ł��������B
���@�̉��������ROM������̌��؎����ł��B

## �e�ʂƃ����[�X�̏���

�㗬��generic BoardConfig�ɂ�2GiB��system�T�C�Y�ݒ肪����܂����A�����CTZ�̎����e�ʂł͂���܂���B
�����ł͕ύX�����A�����e�ʂƂ̈�v���m�F�����܂Ő����C���[�W���������߂�Ƃ͔��f���܂���B
1GB��microSD�ɓW�J�ς݃C���[�W�����邱�Ƃ��O��ɂ��܂���B
stock�ۑ��E�����EAVB�E�p�l�����فE�N�����O�ƑS�n�[�h�E�F�A���؂��K�v�ł��B
�c�[���̏o�͂͏�� `flashReady: false`�A`fullAndroidBuildTested: false` �ł��B

## ���͈ؔ�

�I�t���C���e�X�g�͌����A���ۏ����A�o�b�N�A�b�v�A��x�ڂ̓K�p�AMake���̓��{�ꏉ���l���m�F���܂��B
Make�e�X�g�͊ȈՃn�[�l�X�ł���A�{����AOSP���i�p��������R���p�C�����Č����܂���B
�J�����ɂ͌Œ肵���㗬10�t�@�C���̎��f�[�^�ł�CLI�̌����E�K�p�E�Ď��s���m�F���܂������A
������S�\�[�X�r���h����@�e�X�g�ł͂���܂���B
