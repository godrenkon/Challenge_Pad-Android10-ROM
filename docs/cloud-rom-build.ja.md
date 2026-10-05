# OS�{�̂̃N���E�h�r���h

## ���ԏ���Œ�~�����ꍇ�̃R���p�C���L���b�V��

2026-10-04��run `37188392199` �́A4�����89%�܂Ői�݂܂������A315����
�ēv���Z�X�̏���ɒB���Ē�~���܂����B�����C���[�W�͂���܂���B
�W��GitHub-hosted runner�̓W���u�S�̂�6���Ԃ܂łȂ̂ŁA�P���ȏ�������ł͉������܂���B

���̈Ăł́A�����\�[�X�E���i�E�r���h�c�[���̑g�ݍ��킹�ɂ��āAccache��7G�ɐ������A
���s���ɂ��ۑ����܂��B����̓L���b�V������v����C/C++�̃R���p�C�����ʂ��ė��p�ł��܂��B
�ŏ��̎��s�͋�̃L���b�V������n�܂�A���ԓ��̊����͕ۏ؂��܂���BJava�A�����N�����A
�C���[�W�����Ȃǂ͍Ď��s����܂��B�L���b�V���̗e�ʐݒ��GitHub�̊��������ύX���܂���B

�L���b�V���̃L�[�͈����������V�s�̃n�b�V�����܂߂܂��B���S��v���Ȃ���Γ���OS��
`ctz-compiler-v1` �L���b�V�����畜�����Accache���R���p�C���̓��e�E�\�[�X�E�I�v�V��������
�����������ʂ������ė��p���܂��B���i�p�b�P�[�W�ꗗ�̏C���ł�C/C++�̌��ʂ��ė��p���邽�߂ł��B
�Â� `OUT_DIR` �⊮���C���[�W�͕������܂���B�ύX��̃L�[�����ۑ��Ȃ�A���s���ɂ��V�����L�[�ŕۑ����܂��B
���̈Ă͐V����OUT_DIR�Ɗ����C���[�W�̌��؂��ێ����A�Â�system.img���ė��p���܂���B

�Q�l: [GitHub��6���Ԑ���](https://docs.github.com/en/actions/reference/limits)�A
[�Œ肵��Android 10��ccache�ݒ�](https://github.com/phhusson/platform_build/blob/165f02822b54b3651fb388fc425ea9f3b416b496/core/ccache.mk)�B

`Compile Android 10 systemimage` �́A753�v���W�F�N�g�̃\�[�X�𓯊����A�Scommit���L�^�A
���i������K�p���� `lunch suiram_ctz10-userdebug` �� `m systemimage` �����s����H���ł��B
���̓A�v���P�̂̃r���h��A�z�z�ς�GSI�̖��O�ύX�ł͂���܂���B

�������̖ڕW�́ANEXT�Œʏ�̃z�[����ʁE�ݒ�E�A�v���C���X�g�[�����g����Android 10�ł��B
����boot/kernel/vendor���g���Asystem��PHH�nAOSP Android 10�֒u��������\���ł��B
Google Play/GMS�͂��̐��i�Ɋ܂߂Ă��܂���B�[���ł̋N���ƑS�n�[�h�E�F�A����͖��m�F�ł��B

## ���s���Ɛ��ʕ�

GitHub-hosted Ubuntu 22.04�̎g���̂�runner�ŁA�r���h�ɕs�v�ȃv���C���X�g�[��SDK�����폜���A
�z�X�g�ˑ��ƌŒ�Repo launcher��p�ӂ��܂��B���[�U�[��PC�ɂ͓K�p���܂���B
�\�[�X�͌Œ�revision�̑S�v���W�F�N�g���A�󂢗����Eblob�x���擾�œ������܂��B
�㗬manifest��Darwin�p�Ǝw�肳�ꂽMac�z�X�g��p9�v���W�F�N�g��������Linux�p753�v���W�F�N�g���擾���܂��B
Linux��ARM/ARM64�R���p�C���A�t���[�����[�N�AVNDK 28�݊��R�[�h�͎c���܂��B�S�擾�Ώۂ�commit�ƍ����ێ����܂��B
�[���֏������ޏ����͂���܂���B

�\�[�X�ƒ��Ԑ������́Arunner�̐V�Ksparse�t�@�C����ɍ��Btrfs�֕ۑ����A
`compress-force=zstd:3` �œ��߈��k���܂��B256GiB�͉��z�e�ʂł���A���e�ʂ𑝂₷�����ł͂���܂���B
�擾�O�Ɏ��ۂ̃}�E���g�ƈ��kprobe���m�F���A�ʂ�CI�ł����z�X�g��̈��k��C�R���p�C�����������܂��B
�Ď��ł͓���Btrfs�ƊO��runner�f�B�X�N�̋󂫂̏����������g���܂��B
���k�������Ȃ��f�[�^�����邽�߁A����ł�������ۏ؂��܂���B

�ʏ�̃��[�J���H����400GiB/150GiB�̕ێ�I�|���V�[���ێ����܂��B
�N���E�h�̎��s�͓����O60GiB�E�r���h�O20GiB�E�L��RAM8GiB���J�n�����ɂ��܂��B
����́u���̗e�ʂŕK����������v�Ƃ�������ł͂Ȃ��A�e�ʂ𑪂�Ȃ���i�߂�����ł��B
GitHub-hosted runner�ł̂ݎg��������Ƃ��ĕ������A�e�ʕs����R���p�C�����s�͎��s�Ƃ��ċL�^���܂��B
�\�[�X������4����ł��B�R���p�C���͎���������14GiB�ȏ�Ȃ���4����A
���ꖢ���Ȃ���2����Ƃ��A����������o����CPU���𒴂��܂���BCPU�����s���Ȃ�1����ł��B
2026-10-04�̎��s���O�Ŏ���������16,765,415,424 bytes���m�F�������߁A���̏C���łɂ��̑I����ǉ����܂����B
�擾�E�R���p�C���̍H�����O�����s���ɂ��\�����A
10�b���ƂɌo�ߎ��ԂƋ󂫗e�ʂ��L�^���܂��B�󂫗e��3GiB�����܂��͏�������315����
Repo�E�R���p�C�����܂ޏ����O���[�v���~���A���O�ۑ��p�̎��ԂƗe�ʂ��c���܂��B
GitHub���̖{��step����330���Ajob����355�����O�ɒ�~����݌v�ł��B
�������m�F����O��ROM�����Ƃ͈����܂���B

�������� `android10-systemimage-engineering-untested` artifact�Ɉ��ksystem.img��SHA256������܂��B
�����E�ʏ�̎��s�Ƃ� `android10-systemimage-build-report` �ɍH�����O�A���݂���source lock�E�r���hreceipt��ۑ����܂��B
runner���̂̏����ȂǁA�㑱step�����s����Ȃ��ꍇ��artifact��ۑ��ł��܂���B
�ǂ����30���ۑ��ł��B���ʕ���Git�̃\�[�X�c���[�֓���܂���B

�{�̃r���h������́A�ʂ� `Verify compiled Android 10 image contents` �������œ����܂��B
�������|�W�g���̐���run���琬�ʕ����擾���A���kSHA256�A�W�J�A�ǂݎ���pe2fsck�A
Android 10 / SDK29 / ARM64 / ���i���AADB�F�؂�USB�ݒ�A��{�A�v���̃t�@�C�����݂��������܂��B
Android 10��GSI�ɓ����� `product` / `product_services` �̃A�v���z�u�������Ώۂł��B
VNDK 28�p��32bit ARM�E64bit AArch64�� `libstdc++.so` ��linker�ݒ�̑��݂��������܂��B
����͈ꕔ�̌݊��t�@�C���̎��^�m�F�ł���A�Svendor���C�u�����EHAL�̓���ۏ؂ł͂���܂���B
PHH�̊O�����o�[�X�f�o�b�O�p3�t�@�C�����܂܂�Ȃ����Ƃ��������܂��B
Android 10��userdebug�㏈����USB�� `mtp` �� `adb` ��ǉ����邽�߁A`mtp,adb` ���������o�͂Ƃ��Ĉ����܂��B
�A�v���̑��݊m�F�͎��s�e�X�g�ł͂���܂���B������������JSON���|�[�g��ۑ����܂��B
����system�C���[�W�֏������݁Emount�͂��܂���B

�\�[�X�擾�E�R���p�C���E�C���[�W�����ECTZ�ł̋N���͕ʂ̌��ؒi�K�ł��B
system.img�����ɐ������Ă��A�����p�[�e�B�V�����e�ʁAAVB�����A������i�A���@���؂������܂�
���������C���X�g�[���pROM�Ƃ��Ĕz�z���܂���B

## ���ۂ̎��s�L�^

[����̖{�̃r���h](https://github.com/godrenkon/Challenge_Pad-Android10-ROM/actions/runs/37159364657)
��2026-10-03 22:42 UTC�ɊJ�n���A2026-10-04 04:28 UTC�Ɏ��s�ŏI�����܂����B
�z�X�g�����͐������܂������A�\�[�X�����E�R���p�C���̕���step���i�s���̂܂܏I�����Ă��܂��B
���O�ۑ�step�͖����s�Aartifact��0���Ajob���O�̎擾��BlobNotFound�ł����B
�S���������E�R���p�C���J�n�Esystem.img�����͊m�F�ł����A��~�����͖�����ł��B
���̌��ʂ��󂯂āA���s�����O�\���Ɨe�ʁE���Ԃ̊Ď���ǉ����čĎ��s���܂��B

[�Ď��s](https://github.com/godrenkon/Challenge_Pad-Android10-ROM/actions/runs/37178988640)�́A
�S�\�[�X�����Acommit�L�^�A���i�����̓K�p��ʉ߂��A2026-10-04 05:26:26 UTC�Ɏ��R���p�C�����J�n���܂����B
���i�� `suiram_ctz10-userdebug`�AAndroid 10�ł��B07:53:58 UTC��Ninja 106,558�H����77,882�H����
�󂫗e�ʂ�2,970,992,640 bytes�܂Ō��������߁A3GiB�̕ۑ��p�\�������Ē�~���܂����B
����͏��v���Ԃ�ڐA�H���S�̂�73%�Ƃ����Ӗ��ł͂���܂���B
�R���p�C���̃G���[�ł͂Ȃ��e�ʕs���ɂ�鐧���~�ł��B�r���h���|�[�g��884,848 bytes�Ŏ擾�ł��A
11�t�@�C���̃��O�Elock�Ereceipt�E�ŏI�f�B�X�N�󋵂��m�F���܂����Bsystem.img�͐�������Ă��܂���B
�\�[�X������̋󂫂�44,620,001,280 bytes�ł����B���̎������󂯁AMac�z�X�g��p�\�[�X�̏��O��
���Ԑ��������܂ރr���h�̈�̓��߈��k��ǉ����܂����B

���k�̈��[��runner����](https://github.com/godrenkon/Challenge_Pad-Android10-ROM/actions/runs/37188221202)��
2026-10-04 08:15:32 UTC�ɐ������܂����BBtrfs�� `compress-force=zstd:3` mount�A
9,437,184 bytes�̎����f�[�^��294,912 bytes��extents�ɂȂ邱�ƁA���̗̈��C�v���O�������R���p�C���E���s�ł��邱�Ƃ��m�F���Ă��܂��B
���̎����f�[�^�̈��k����Android�\�[�X�⒆�Ԑ������̈��k���Ƃ݂͂Ȃ��܂���B
��runner�̊O���̋󂫂�119,519,567,872 bytes�ł����B�\�[�X�EWindows PowerShell�ELinux PowerShell��CI���������Ă��܂��B
Ubuntu 22.04�̈��k�m�F�c�[���� `btrfs-compsize` �p�b�P�[�W����񋟂���� `compsize` ���g���܂��B
�C���ł�manifest commit `38974bf7945751ad9eb38e29420c329c07f56a89` ���擾���A
�N���v�� `2026-10-04-disk-capacity-02` �ŋ��\����run��u�������܂��B

�Ď��s���ɁAPHH�� `system.prop` ��ADB�F�ؖ����̐ݒ肪�c������m�F���܂����B
`base.mk` �� `system.prop` �̗������C�����A�㗬10�t�@�C���̎��f�[�^�ւ̓K�p���m�F���Ă��܂��B
���łɊJ�n�ς݂�run�֌ォ��\�[�X�����𒍓����܂���B
`Queue updated ROM recipe` �͖{��run�I�����ɁA����commit�ƍŐVmain�̃r���h����blob���r���܂��B
���͂��ς��A����main commit�ɂ�����̃r���h���͂�����commit�ɂ��{�̃r���h�̎��s���܂��Ȃ���΁A�C���ł̖{�̃r���h��
`workflow_dispatch` ��1��J�n���܂��B���������̍X�V�E�������́E���s�ς�commit�ł͊J�n���܂���B
�L�����Z�����ꂽrun����������J�n���܂���B
��r������͂� `scripts/queue-updated-rom-build.cjs` �� `INPUTS` �ɗ񋓂��Ă��܂��B
����workflow�� `actions: write` �͖{��workflow�̊J�n�Ɏg���A�[������⃊���[�X���J�͍s���܂���B
�{��workflow�� `workflow_dispatch`�A�܂��� `.github/rom-build-request.json` �̖����I�ȋN���v���ŊJ�n���܂��B
�ʏ�̃\�[�X�C��push�ł͊J�n���܂���B�V���������I�ȋN���v����concurrency group���̌Â��{��run�𒆎~���A�ŐV�̏C���łɒu�������܂��B
����������push�ł͖{��run���J�n�E���~���܂���B
concurrency�ݒ�ǉ��O�ɊJ�n��������run�́A����group�Ɋ܂܂�܂���B
2026-10-04�̋N���v���́A�C���ς݂�ADB�ݒ�ƕ��񐔑I�����܂�main�̖{�̃r���h���J�n���邽�߂̂��̂ł��B
����ŊJ�n����commit�̖{��run������΁A���Ŋ�����̎����ăr���h�������d�����ĊJ�n���܂���B
�����X�V��main���i��ł��A�������|�W�g����main�Ŋ��Ɏ��s�����S�r���h���͂�blob��v���m�F���ďd����h���܂��B
�蓮�̏ꍇ�́A[�{��workflow](https://github.com/godrenkon/Challenge_Pad-Android10-ROM/actions/workflows/rom-build.yml)
�� `Run workflow` ���疾���I�ɊJ�n���܂��B
