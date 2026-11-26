# x86_64 Linux — Hello world via syscalls (no libc)
# Assemble: clang -nostdlib -static -o hello hello.s
#        or: as -o hello.o hello.s && ld -o hello hello.o

        .global _start
        .text

_start:
        mov     $1, %rax            # sys_write
        mov     $1, %rdi            # fd = stdout
        lea     msg(%rip), %rsi     # buffer
        mov     $msg_len, %rdx      # length
        syscall

        mov     $60, %rax           # sys_exit
        xor     %rdi, %rdi          # status 0
        syscall

        .section .rodata
msg:
        .ascii  "Hello from assembly\n"
        .equ    msg_len, . - msg
