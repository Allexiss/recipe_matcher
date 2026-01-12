create table users (
    id int auto_increment primary key,
    username varchar(50) not null
);

# test insert user
insert into users (username) values ('john');
select * from users;

# delete test
delete from users;

create table groceries (
    name varchar(100) primary key,
    amount int
);